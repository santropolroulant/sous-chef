from functools import reduce

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from souschef.order.models import Order


class KitchenCountOrderFilter(django_filters.FilterSet):
    """Defines the filters used to filter orders in the Kitchen Count."""

    client_name = django_filters.CharFilter(
        method="filter_client", label=_("Search by client name")
    )

    class Meta:
        model = Order
        fields = ["creation_date", "delivery_date", "status", "client"]

    def filter_client(self, queryset, field_name, value):
        """Filters the orders using client names."""
        if not value:
            return queryset

        bits = value.split(" ")
        queryset = queryset.filter(
            reduce(
                lambda q, name: q
                | Q(client__member__firstname__icontains=name)
                | Q(client__member__lastname__icontains=name),
                bits,
                Q(),
            )
        )

        return queryset
