from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
)

from souschef.order.constants import ORDER_STATUS
from souschef.order.models import Order


class OrderFilter(FilterSet):
    name = CharFilter(method="filter_search", label=_("Search by name"))

    status = ChoiceFilter(choices=(("", ""),) + ORDER_STATUS)

    class Meta:
        model = Order
        fields = ["status", "delivery_date"]

    def filter_search(self, queryset, field_name, value):
        if not value:
            return queryset

        names = value.split(" ")

        name_contains = Q()

        for name in names:
            firstname_contains = Q(client__member__firstname__icontains=name)

            name_contains |= firstname_contains

            lastname_contains = Q(client__member__lastname__icontains=name)
            name_contains |= lastname_contains

        return queryset.filter(name_contains)


class DeliveredOrdersByMonthFilter(FilterSet):
    delivery_date = CharFilter(method="filter_period")

    class Meta:
        model = Order
        fields = ["creation_date", "delivery_date", "status", "client"]

    def filter_period(self, queryset, field_name, value):
        if not value:
            return None

        year, month = value.split("-")
        return queryset.filter(
            status="D",
            delivery_date__year=year,
            delivery_date__month=month,
        )
