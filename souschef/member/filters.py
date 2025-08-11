from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    MultipleChoiceFilter,
)

from souschef.member.constants import DELIVERY_TYPE
from souschef.member.models import Client, ClientScheduledStatus


class ClientScheduledStatusFilter(FilterSet):
    class Meta:
        model = ClientScheduledStatus
        fields = ["operation_status"]


class ClientFilter(FilterSet):
    name = CharFilter(method="filter_search", label=_("Search by name"))

    status = MultipleChoiceFilter(choices=Client.CLIENT_STATUS)

    delivery_type = ChoiceFilter(choices=(("", ""),) + DELIVERY_TYPE)

    class Meta:
        model = Client
        fields = ["route", "status", "delivery_type"]

    def filter_search(self, queryset, field_name, value):
        if not value:
            return queryset

        name_contains = Q()
        names = value.split(" ")

        for name in names:
            firstname_contains = Q(member__firstname__icontains=name)

            lastname_contains = Q(member__lastname__icontains=name)

            name_contains |= firstname_contains | lastname_contains

        return queryset.filter(name_contains)
