import calendar
import csv
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Tuple, Union, cast

from django.http import HttpResponse
from typing_extensions import Literal

from souschef.meal.constants import (
    COMPONENT_GROUP_CHOICES,
    COMPONENT_GROUP_CHOICES_MAIN_DISH,
)
from souschef.member.constants import RATE_TYPE_LOW_INCOME
from souschef.order.constants import ORDER_ITEM_TYPE_CHOICES_COMPONENT

if TYPE_CHECKING:
    from souschef.billing.models import Billing
    from souschef.member.models import Client
    from souschef.member.types import RateType
    from souschef.order.models import Order, Order_item

CSV_HEADER = [
    "Nº de facture",
    "Client",
    "Courriel",
    "Modalités",
    "Date de facturation",
    "Échéance",
    "Produit/service",
    "Description",
    "Qté",
    "Taux",
    "Montant",
    "Classe",
]

MAIN_DISH_DESCRIPTION_OVERRIDE = "Repas"

# tuple of component group, meal size, unit price
GroupKey = Tuple[str, Union[str, None], Decimal]


@dataclass
class GroupedItem:
    """Used to calculate total quantity for items sharing the same key."""

    component: str
    description: str
    size: Union[Literal["R", "L"], None]
    unit_price: Decimal
    is_billable: bool
    quantity: int = 0

    @property
    def group_key(self) -> GroupKey:
        return (self.component, self.size, self.unit_price)

    @classmethod
    def from_order_item(cls, item: "Order_item") -> "GroupedItem":
        if item.component_group is None:
            # Items with component_group having value of None should be filtered
            # before constructing GroupedItem.
            raise ValueError("item with component_group None")
        component_descriptions = dict(COMPONENT_GROUP_CHOICES)
        component_descriptions[COMPONENT_GROUP_CHOICES_MAIN_DISH] = (
            MAIN_DISH_DESCRIPTION_OVERRIDE
        )
        return GroupedItem(
            component=item.component_group,
            description=(component_descriptions.get(item.component_group, "")),
            size=cast(Union[Literal["R", "L"], None], item.size),
            unit_price=(
                item.price / item.total_quantity if item.billable_flag else Decimal(0)
            ),
            is_billable=item.billable_flag,
        )


def _get_billing_date(billing_year: int, billing_month: int):
    return (
        f"{billing_year}-"
        f"{str(billing_month).zfill(2)}-"
        f"{calendar.monthrange(billing_year, billing_month)[1]}"
    )


def _get_row_prefix(billing: "Billing", client: "Client"):
    billing_date = _get_billing_date(billing.billing_year, billing.billing_month)
    return [
        # We use the client ID as the invoice number as to group invoice lines
        # together. Quickbooks will replace this number when generating the invoices.
        client.id,
        f"{client.member.lastname}, {client.member.firstname}",
        client.billing_email,
        "Payable dès réception",
        billing_date,
        billing_date,
    ]


def _get_invoice_row(
    *,
    product: str,
    description: str,
    quantity: int,
    unit_price: Decimal,
    class_: str = "2 - Béatrice:Popote - Clients",
):
    return [
        product,
        description,
        quantity,
        unit_price,
        quantity * unit_price,
        class_,
    ]


def _get_row_for_group(item_group: GroupedItem, rate_type: "RateType"):
    if (
        item_group.component == COMPONENT_GROUP_CHOICES_MAIN_DISH
        and item_group.size == "R"
    ):
        product = (
            "Popote roulante_Low income"
            if rate_type == RATE_TYPE_LOW_INCOME
            else "Popote roulante"
        )

    elif (
        item_group.component == COMPONENT_GROUP_CHOICES_MAIN_DISH
        and item_group.size == "L"
    ):
        product = (
            "Popote roulante_Low income Large"
            if rate_type == RATE_TYPE_LOW_INCOME
            else "Popote roulante_Repas Large"
        )

    else:
        product = (
            "Popote roulante_Extra Low Income"
            if rate_type == RATE_TYPE_LOW_INCOME
            else "Popote roulante_Extra"
        )

    if (
        item_group.component == COMPONENT_GROUP_CHOICES_MAIN_DISH
        and not item_group.is_billable
    ):
        product = (
            "Popote roulante_Large_non-chargé"
            if item_group.size == "L"
            else "Popote roulante_non-chargé"
        )

    if item_group.quantity > 0:
        yield _get_invoice_row(
            product=product,
            description=item_group.description,
            quantity=item_group.quantity,
            unit_price=item_group.unit_price,
        )


def _get_grouped_items(orders: "List[Order]") -> List[GroupedItem]:
    groups: Dict[GroupKey, GroupedItem] = dict()
    for order in orders:
        for item in order.orders.all():
            item: Order_item
            if item.order_item_type != ORDER_ITEM_TYPE_CHOICES_COMPONENT:
                continue

            if item.component_group is None:
                continue

            # For main dishes we show items that are non-billable on the invoice.
            # For sides we hide them.
            if (
                item.component_group != COMPONENT_GROUP_CHOICES_MAIN_DISH
                and not item.billable_flag
            ):
                continue

            new_group = GroupedItem.from_order_item(item)
            item_key = new_group.group_key
            if item_key not in groups:
                groups[item_key] = new_group

            group = groups[item_key]
            group.quantity += item.total_quantity

    return list(groups.values())


def _get_invoice_rows(orders: "List[Order]", rate_type: "RateType"):
    for group in _get_grouped_items(orders):
        yield from _get_row_for_group(group, rate_type)


def _get_client_rows(billing: "Billing", client: "Client", orders: "List[Order]"):
    first_row_prefix = _get_row_prefix(billing, client)
    non_first_row_prefix = [client.id] + [""] * 5
    is_first_row = True
    for row in _get_invoice_rows(orders, cast("RateType", client.rate_type)):
        prefix = first_row_prefix if is_first_row else non_first_row_prefix
        yield prefix + row
        is_first_row = False


def _get_rows(billing: "Billing"):
    for client, orders in billing.client_orders.items():
        yield from _get_client_rows(billing, client, orders)


def export_csv(billing: "Billing"):
    response = HttpResponse(content_type="text/csv")
    billing_date = _get_billing_date(billing.billing_year, billing.billing_month)
    response["Content-Disposition"] = (
        f"attachment; filename={billing_date}_sous_chef_billing.csv"
    )
    writer = csv.writer(response, csv.excel)
    writer.writerow(CSV_HEADER)

    writer.writerows(_get_rows(billing))

    return response
