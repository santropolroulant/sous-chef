from django.db.models import (
    Q,
)
from django.utils.translation import gettext_lazy as _
from django_filters import (
    CharFilter,
    FilterSet,
)

from souschef.billing.models import Billing


class BillingFilter(FilterSet):
    name = CharFilter(method="filter_search", label=_("Search by name"))
    date = CharFilter(method="filter_period")

    class Meta:
        model = Billing
        fields = ["name", "date"]

    def filter_search(self, queryset, field_name, value):
        if not value:
            return queryset

        name_contains = Q()
        names = value.split(" ")

        for name in names:
            firstname_contains = Q(client__member__firstname__icontains=name)
            lastname_contains = Q(client__member__lastname__icontains=name)
            name_contains |= firstname_contains | lastname_contains

        return queryset.filter(name_contains)

    def filter_period(self, queryset, field_name, value):
        if not value:
            return queryset

        year, month = value.split("-")
        return queryset.filter(billing_year=year, billing_month=month)
