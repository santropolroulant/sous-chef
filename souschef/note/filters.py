from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import (
    CharFilter,
    ChoiceFilter,
    DateFromToRangeFilter,
    FilterSet,
)

from souschef.note.models import Note


class NoteFilter(FilterSet):
    IS_READ_CHOICES = (
        ("", "All"),
        ("1", "Yes"),
        ("0", "No"),
    )

    NOTE_STATUS_UNREAD = IS_READ_CHOICES[2][0]

    is_read = ChoiceFilter(
        choices=IS_READ_CHOICES,
    )

    name = CharFilter(method="filter_search", label=_("Search by name"))

    date_modified = DateFromToRangeFilter(lookup_expr="contains")

    class Meta:
        model = Note
        fields = [
            "priority",
            "is_read",
            "date_modified",
            "category",
        ]

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
