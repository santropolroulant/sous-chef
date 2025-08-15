import collections
from datetime import (
    date,
    datetime,
)
from typing import DefaultDict, Dict, List, Sequence, TypedDict

from annoying.fields import JSONField
from django.db import models
from django.db.models import (
    Prefetch,
)
from django.utils.translation import gettext_lazy as _

from souschef.member.models import Client
from souschef.order.models import (
    Order,
    Order_item,
)


class BillingManager(models.Manager):
    def billing_create_new(self, year, month):
        """
        Create a new billing for the given period.
        A period is a month.
        """
        # Get all billable orders for the given period
        billable_orders = (
            Order.objects.get_billable_orders(year, month)
            .select_related("client__member")
            .only("client__member__firstname", "client__member__lastname")
            .prefetch_related(
                Prefetch(
                    "orders",
                    queryset=Order_item.objects.all().only(
                        "order__id", "price", "billable_flag"
                    ),
                )
            )
        )

        total_amount = calculate_amount_total(billable_orders)

        # Create the Billing object
        billing = Billing.objects.create(
            total_amount=total_amount,
            billing_month=month,
            billing_year=year,
            created=datetime.today(),
            detail={},
        )

        # Attach the orders
        billing.orders.add(*billable_orders)

        return billing

    def billing_get_period(self, year, month):
        """
        Check if a billing exists for a given period.
        Return None otherwise.
        """
        billing = Billing.objects.filter(
            billing_year=year,
            billing_month=month,
        )

        if billing.count() == 0:
            return None
        else:
            return billing


class RegularLargeDict(TypedDict):
    R: int
    L: int


class OrderSummaryDict(TypedDict):
    total_orders: int
    total_main_dishes: RegularLargeDict
    total_billable_extras: int
    total_amount: int


class Billing(models.Model):  # noqa: DJ008
    class Meta:
        ordering = ["-billing_year", "-billing_month"]

    total_amount = models.DecimalField(
        verbose_name=_("total_amount"), max_digits=8, decimal_places=2
    )

    # Month start with january is 1
    billing_month = models.IntegerField()

    billing_year = models.IntegerField()

    created = models.DateTimeField(verbose_name=None, auto_now=True)

    detail = JSONField()

    orders = models.ManyToManyField(Order)

    objects = BillingManager()

    @property
    def billing_period(self):
        """
        Return a readable format for the billing period.
        """
        period = date(self.billing_year, self.billing_month, 1)
        return period

    @property
    def client_orders(self) -> DefaultDict[Client, List[Order]]:
        client_orders = collections.defaultdict(list)
        for order in self.orders.all():
            client_orders[order.client].append(order)
        return client_orders

    @property
    def summary(self) -> dict[Client, OrderSummaryDict]:
        """
        Return a summary of every client.
        Format: dictionary {client: info}
        """
        result: Dict[Client, OrderSummaryDict] = {}
        for client, orders in self.client_orders.items():
            result[client] = {
                "total_orders": len(orders),
                "total_main_dishes": {"R": 0, "L": 0},  # to be counted
                "total_billable_extras": 0,  # to be counted
                "total_amount": sum(map(lambda o: o.price, orders)),
            }
            for order in orders:
                for item in order.orders.all():
                    item: Order_item
                    if item.component_group == "main_dish":
                        if item.size == "R":
                            result[client]["total_main_dishes"]["R"] += (
                                item.total_quantity
                            )
                        elif item.size == "L":
                            result[client]["total_main_dishes"]["L"] += (
                                item.total_quantity
                            )
                    else:
                        if item.billable_flag is True:
                            result[client]["total_billable_extras"] += (
                                item.total_quantity
                            )
        return result


# get the total amount from a list of orders
def calculate_amount_total(orders: Sequence[Order]):
    total = 0
    for order in orders:
        total += order.price
    return total
