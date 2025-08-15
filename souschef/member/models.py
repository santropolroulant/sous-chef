from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Tuple

from annoying.fields import JSONField
from django.db import models
from django.db.models import Q
from django.db.models.functions import Extract
from django.forms import ValidationError
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django_filters import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    MultipleChoiceFilter,
)

from souschef.meal.constants import (
    COMPONENT_GROUP_CHOICES,
    COMPONENT_GROUP_CHOICES_SIDES,
)
from souschef.member.constants import (
    CELL,
    CONTACT_TYPE_CHOICES,
    DAYS_OF_WEEK,
    DEFAULT_VEHICLE,
    DELIVERY_TYPE,
    EMAIL,
    GENDER_CHOICES,
    HOME,
    MAILING_TYPE,
    OPTION_GROUP_CHOICES,
    PAYMENT_TYPE,
    RATE_TYPE,
    ROUTE_VEHICLES,
    WORK,
)
from souschef.member.formsfield import CAPhoneNumberExtField
from souschef.note.models import Note


class Member(models.Model):
    class Meta:
        verbose_name_plural = _("members")

    mid = models.IntegerField(blank=True, null=True)

    rid = models.IntegerField(blank=True, null=True)

    # Member information
    firstname = models.CharField(max_length=50, verbose_name=_("First name"))

    lastname = models.CharField(max_length=50, verbose_name=_("Last name"))

    address = models.OneToOneField(
        "member.Address",
        verbose_name=_("address"),
        null=True,
        on_delete=models.SET_NULL,
    )

    work_information = models.TextField(
        verbose_name=_("Work information"),
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.firstname} {self.lastname}"

    @property
    def home_phone(self):
        try:
            val_orig = next(
                mc.value for mc in self.member_contact.all() if mc.type == HOME
            )
            f = CAPhoneNumberExtField()
            val_clean = f.clean(val_orig)
            if val_orig != val_clean:
                self.member_contact.filter(type=HOME).first().value = val_clean
                self.add_contact_information(HOME, val_clean, True)
                return val_clean
            return val_orig
        except ValidationError:
            return val_orig
        except Exception:
            return ""

    @property
    def cell_phone(self):
        try:
            val_orig = next(
                mc.value for mc in self.member_contact.all() if mc.type == CELL
            )
            f = CAPhoneNumberExtField()
            val_clean = f.clean(val_orig)
            if val_orig != val_clean:
                self.member_contact.filter(type=CELL).first().value = val_clean
                self.add_contact_information(CELL, val_clean, True)
                return val_clean
            return val_orig
        except ValidationError:
            return val_orig
        except Exception:
            return ""

    @property
    def work_phone(self):
        try:
            val_orig = next(
                mc.value for mc in self.member_contact.all() if mc.type == WORK
            )
            f = CAPhoneNumberExtField()
            val_clean = f.clean(val_orig)
            if val_orig != val_clean:
                self.member_contact.filter(type=WORK).first().value = val_clean
                self.add_contact_information(WORK, val_clean, True)
                return val_clean
            return val_orig
        except ValidationError:
            return val_orig
        except Exception:
            return ""

    @property
    def email(self):
        try:
            return next(
                mc.value for mc in self.member_contact.all() if mc.type == EMAIL
            )
        except Exception:
            return ""

    def add_contact_information(self, type, value, force_update=False):
        """
        Attach a new contact information to the member instance.
        If a contact information of the given type already exists, it should be
        updated. Otherwise, it should create a new one.
        """
        created = False
        if value is None:
            value = ""

        if force_update or value != "":
            contact, created = Contact.objects.update_or_create(
                member=self, type=type, defaults={"value": value, "member": self}
            )
        return created


class Address(models.Model):
    class Meta:
        verbose_name_plural = _("addresses")
        ordering = ["number", "street", "apartment"]

    # Member address information
    number = models.PositiveIntegerField(
        verbose_name=_("street number"),
        blank=True,
        null=True,
    )

    street = models.CharField(max_length=100, verbose_name=_("street"))

    # Can look like B02 so can't be an IntegerField
    apartment = models.CharField(
        max_length=10,
        verbose_name=_("apartment"),
        blank=True,
        null=True,
    )

    floor = models.IntegerField(
        verbose_name=_("floor"),
        blank=True,
        null=True,
    )

    city = models.CharField(max_length=50, verbose_name=_("city"))

    # Montreal postal code look like H3E 1C2
    postal_code = models.CharField(max_length=7, verbose_name=_("postal code"))

    region_code = models.CharField(
        max_length=10, verbose_name=_("province"), default="QC"
    )

    country_code = models.CharField(
        max_length=10, verbose_name=_("country"), default="CA"
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )

    distance = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )

    def __str__(self):
        first_line = []
        first_line.append(str(self.street))
        if self.apartment:
            first_line.append(f"Apt.{self.apartment}")
        if self.floor:
            first_line.append(f"{self.floor} Floor")

        first_line = " ".join(first_line)
        second_line = f"{self.city}, {self.postal_code}"

        return f"{first_line}, {second_line}"


class Contact(models.Model):
    class Meta:
        verbose_name_plural = _("contacts")

    # Member contact information
    type = models.CharField(
        max_length=100, choices=CONTACT_TYPE_CHOICES, verbose_name=_("contact type")
    )

    value = models.CharField(max_length=50, verbose_name=_("value"))

    member = models.ForeignKey(
        "member.Member",
        verbose_name=_("member"),
        related_name="member_contact",
        on_delete=models.CASCADE,
    )

    def display_value(self):
        if self.type in (HOME, WORK, CELL):
            try:
                f = CAPhoneNumberExtField()
                return f.clean(self.value)
            except ValidationError:
                return self.value
            except Exception:
                return ""
        return self.value

    def __str__(self):
        return f"{self.member.firstname} {self.member.lastname}"


class Route(models.Model):
    class Meta:
        verbose_name_plural = _("Routes")
        ordering = ["name"]

    name = models.CharField(max_length=50, verbose_name=_("name"))

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        null=True,
    )

    vehicle = models.CharField(
        max_length=20,
        choices=ROUTE_VEHICLES,
        verbose_name=_("vehicle"),
        default=DEFAULT_VEHICLE,
    )

    client_id_sequence = JSONField(
        verbose_name=_("IDs of clients on this route (as a JSON list)"), default=[]
    )

    def __str__(self):
        return self.name


class DeliveryHistory(models.Model):
    class Meta:
        verbose_name = _("Delivery History")
        verbose_name_plural = _("Delivery Histories")
        ordering = ["route", "-date"]
        unique_together = ("route", "date")

    route = models.ForeignKey(
        "member.Route",
        on_delete=models.CASCADE,
        verbose_name=_("route"),
        related_name="delivery_histories",
    )
    date = models.DateField(verbose_name=_("date of the delivery"))
    vehicle = models.CharField(
        max_length=20, choices=ROUTE_VEHICLES, verbose_name=_("vehicle")
    )
    client_id_sequence = JSONField(
        verbose_name=_("IDs of clients on this route (as a JSON list)"), default=[]
    )
    comments = models.TextField(
        verbose_name=_("comments"),
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"DeliveryHistory: Route {self.route.name} delivered on {self.date}"


class ClientManager(models.Manager):
    def get_birthday_boys_and_girls(self):
        today = datetime.datetime.now()

        clients = self.filter(
            birthdate__year__lte=today.year,
            birthdate__month=today.month,
            birthdate__day__gte=today.day,
            birthdate__day__lte=today.day + 7,
        ).order_by(Extract("birthdate", "day"))

        today = datetime.date.today()
        for client in clients:
            client.age_to_celebrate = today.year - client.birthdate.year

        return clients


class ActiveClientManager(ClientManager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Client.ACTIVE)


class OngoingClientManager(ClientManager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Client.ACTIVE, delivery_type="O")


class PendingClientManager(ClientManager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Client.PENDING)


class ContactClientManager(ClientManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                Q(status=Client.ACTIVE)
                | Q(status=Client.STOPCONTACT)
                | Q(status=Client.PAUSED)
                | Q(status=Client.PENDING)
            )
        )


class BirthdayContactClientManager(ClientManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                Q(status=Client.ACTIVE)
                | Q(status=Client.PAUSED)
                | Q(status=Client.PENDING)
            )
        )


def get_ongoing_clients_at_date(
    the_date: datetime.date, today: datetime.date | None = None
) -> List["Client"]:  # noqa: UP037
    today = today or datetime.date.today()

    # This way of doing things will not work with a very large client database.
    # Hard-to-write optimized SQL queries would be required.
    return [
        client
        for client in Client.objects.filter(delivery_type="O")
        if client.get_status_planned_at_date(the_date, today) == Client.ACTIVE
    ]


class Client(models.Model):
    # Characters are used to keep a backward-compatibility
    # with the previous system.
    PENDING = "D"
    ACTIVE = "A"
    PAUSED = "S"
    STOPNOCONTACT = "N"
    STOPCONTACT = "C"
    DECEASED = "I"

    ONGOING_DELIVERY = "O"
    EPISODIC_DELIVERY = "E"

    CLIENT_STATUS = (
        (PENDING, _("Pending")),
        (ACTIVE, _("Active")),
        (PAUSED, _("Paused")),
        (STOPNOCONTACT, _("Stop: no contact")),
        (STOPCONTACT, _("Stop: contact")),
        (DECEASED, _("Deceased")),
    )

    LANGUAGES = (
        ("en", _("English")),
        ("fr", _("French")),
        ("al", _("Allophone")),
    )

    class Meta:
        verbose_name_plural = _("clients")
        ordering = ["-member__created_at"]

    billing_member = models.ForeignKey(
        "member.Member",
        related_name="+",
        verbose_name=_("billing member"),
        # A client must have a billing member
        on_delete=models.PROTECT,
    )

    billing_payment_type = models.CharField(
        verbose_name=_("Payment Type"),
        max_length=10,
        null=True,
        blank=True,
        choices=PAYMENT_TYPE,
    )

    billing_mailing_type = models.CharField(
        verbose_name=_("Mailing Type"),
        max_length=10,
        null=True,
        blank=True,
        choices=MAILING_TYPE,
    )

    billing_email = models.CharField(
        verbose_name=_("Billing Email"),
        max_length=320,
        null=True,
        blank=True,
    )

    rate_type = models.CharField(
        verbose_name=_("rate type"), max_length=10, choices=RATE_TYPE, default="default"
    )

    member = models.ForeignKey(
        "member.Member", verbose_name=_("member"), on_delete=models.CASCADE
    )

    status = models.CharField(max_length=1, choices=CLIENT_STATUS, default=PENDING)

    language = models.CharField(max_length=2, choices=LANGUAGES, default="fr")

    alert = models.TextField(
        verbose_name=_("alert client"),
        blank=True,
        null=True,
    )

    delivery_type = models.CharField(max_length=1, choices=DELIVERY_TYPE, default="O")

    gender = models.CharField(
        max_length=1,
        default="U",
        blank=True,
        null="True",
        choices=GENDER_CHOICES,
    )

    birthdate = models.DateField(
        auto_now=False, auto_now_add=False, default=timezone.now, blank=True, null=True
    )

    route = models.ForeignKey(
        "member.Route",
        on_delete=models.SET_NULL,
        verbose_name=_("route"),
        blank=True,
        null=True,
    )

    meal_default_week: Dict[str, Any] = JSONField(blank=True, null=True)

    delivery_note = models.TextField(
        verbose_name=_("Delivery Note"), blank=True, null=True
    )

    ingredients_to_avoid = models.ManyToManyField(
        "meal.Ingredient", through="Client_avoid_ingredient"
    )

    components_to_avoid = models.ManyToManyField(
        "meal.Component", through="Client_avoid_component"
    )

    options = models.ManyToManyField("member.option", through="Client_option")

    restrictions = models.ManyToManyField("meal.Restricted_item", through="Restriction")

    def __str__(self):
        return f"{self.member.firstname} {self.member.lastname}"

    objects = ClientManager()

    active = ActiveClientManager()
    pending = PendingClientManager()
    ongoing = OngoingClientManager()
    contact = ContactClientManager()
    birthday_contact = BirthdayContactClientManager()

    @property
    def is_geolocalized(self):
        """
        Returns if the client's address is properly geolocalized.
        """
        return not (
            self.member.address.latitude is None
            or self.member.address.longitude is None
        )

    @property
    def age(self):
        """
        Returns integer specifying person's age in years on the current date.

        To compare the Month and Day they need to be in the same year. Since
        either the birthday can be in a leap year or today can be Feb 29 of a
        leap year, we need to make sure to compare the days, in a leap year,
        therefore we are comparing in the year 2000, which was a leap year.

        >>> from datetime import date
        >>> p = Client(birthdate=date(1950, 4, 19)
        >>> p.age()
        66
        """
        today = datetime.date.today()
        if today < self.birthdate:
            age = 0
        elif datetime.date(
            2000, self.birthdate.month, self.birthdate.day
        ) <= datetime.date(2000, today.month, today.day):
            age = today.year - self.birthdate.year
        else:
            age = today.year - self.birthdate.year - 1
        return age

    @classmethod
    def get_verbose_status(cls, status: str) -> str:
        return dict(cls.CLIENT_STATUS).get(status, _("Unknown"))

    @property
    def status_verbose(self):
        return self.get_verbose_status(self.status)

    @property
    def delivery_type_verbose(self):
        return dict(DELIVERY_TYPE).get(self.delivery_type, _("Unknown"))

    @property
    def orders(self):
        """
        Returns orders associated to this client
        """
        return self.client_order.all()

    def number_of_deliveries_in_month(self, year, month):
        orders = self.client_order.filter(
            status="D", delivery_date__year=year, delivery_date__month=month
        )
        return len(orders)

    @property
    def upcoming_orders(self):
        """
        Returns upcoming orders associated to this client, regardless
        of order status.
        """
        return self.client_order.filter(
            delivery_date__gte=datetime.date.today(),
        ).all()

    @property
    def food_preparation(self):
        """
        Returns specific food preparation associated to this client
        """
        return self.options.filter(option_group="preparation")

    @property
    def notes(self):
        """
        Returns notes associated to this client
        """
        return self.client_notes.all()

    @property
    def simple_meals_schedule(self):
        """
        Returns a list of days, corresponding to the client's delivery
        days.
        """
        for co in self.client_option_set.all():
            if co.option.name == "meals_schedule":
                try:
                    return json.loads(co.value)
                except (ValueError, TypeError):  # JSON error
                    continue
        return None

    @property
    def meals_default(self) -> List[Tuple[str, Dict[str, int | None]]]:
        """
        Returns a list of tuple ((weekday, meal default), ...) that
        represents what the client wants on particular days.

        The "meal default" always contains all available components.
        If not set, it will be None.

        It is possible to have zero value, representing that the client
        has said no to a component on a particular day.
        """
        defaults: List[Tuple[str, Dict[str, int | None]]] = []
        for day, _str in DAYS_OF_WEEK:
            current: Dict[str, int | None] = {}
            for component, _label in COMPONENT_GROUP_CHOICES:
                if component is COMPONENT_GROUP_CHOICES_SIDES:
                    continue  # skip "Sides"
                item_quantity: int | None = self.meal_default_week.get(
                    component + "_" + day + "_quantity"
                )
                current[component] = item_quantity

            size = self.meal_default_week.get("size_" + day)
            current["size"] = size

            defaults.append((day, current))

        return defaults

    @property
    def meals_schedule(self) -> List[Tuple[str, Dict[str, int | None]]]:
        """
        Filters `self.meals_default` based on `self.simple_meals_schedule`.
        Non-scheduled days are excluded from the result tuple.

        Intended to be called only for Ongoing clients. For episodic clients
        or if `simple_meals_schedule` is not set, it returns empty tuple.
        """
        defaults = self.meals_default
        prefs: List[Tuple[str, Dict[str, int | None]]] = []
        simple_meals_schedule = self.simple_meals_schedule

        if (
            self.delivery_type == self.EPISODIC_DELIVERY
            or simple_meals_schedule is None
        ):
            return []
        else:
            for day, meal_schedule in defaults:
                if day in simple_meals_schedule:
                    prefs.append((day, meal_schedule))
            return prefs

    def set_simple_meals_schedule(self, schedule):
        """
        Set the delivery days for the client.
        @param schedule
            A python list of days.
        """
        meal_schedule_option, _ = Option.objects.get_or_create(name="meals_schedule")
        client_option, _ = Client_option.objects.update_or_create(
            client=self,
            option=meal_schedule_option,
            defaults={"value": json.dumps(schedule)},
        )

    def get_status_planned_at_date(
        self, the_date: datetime.date, today: datetime.date | None = None
    ):
        """
        Get the planned `status` the client will have at date `the_date`.

        Applies the latest scheduled `ClientScheduledStatus` and return the resulting
        state.

        `today` can be overriden for unit tests.
        """
        today = today or datetime.date.today()

        planned_status = self.status

        status_changes = (
            self.scheduled_statuses.filter(
                change_date__gte=today,
                change_date__lte=the_date,
                change_state=ClientScheduledStatus.END,
                operation_status=ClientScheduledStatus.TOBEPROCESSED,
            )
            .order_by("-change_date")
            .all()
        )

        if status_changes:
            planned_status = status_changes[0].status_to

        return planned_status


class ClientScheduledStatus(models.Model):
    START = "START"
    END = "END"

    CHANGE_STATUS = (
        (START, _("Start")),
        (END, _("End")),
    )

    TOBEPROCESSED = "NEW"
    PROCESSED = "PRO"
    ERROR = "ERR"

    OPERATION_STATUS = (
        (TOBEPROCESSED, _("To be processed")),
        (PROCESSED, _("Processed")),
        (ERROR, _("Error")),
    )

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="scheduled_statuses"
    )

    pair = models.OneToOneField(
        "self",
        verbose_name=_("Client Scheduled Status Pair"),
        related_name="my_pair",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    status_from = models.CharField(max_length=1, choices=Client.CLIENT_STATUS)

    status_to = models.CharField(max_length=1, choices=Client.CLIENT_STATUS)

    reason = models.CharField(max_length=200, blank=True, default="")

    change_date = models.DateField(
        auto_now=False,
        auto_now_add=False,
        default=timezone.now,
    )

    change_state = models.CharField(max_length=5, choices=CHANGE_STATUS, default=START)

    operation_status = models.CharField(
        max_length=3, choices=OPERATION_STATUS, default=TOBEPROCESSED
    )

    class Meta:
        ordering = ["change_date"]

    def __str__(self):
        return (
            f"Update {self.client.member} status: from "
            f"{self.get_status_from_display()} to {self.get_status_to_display()}, "
            f"on {self.change_date}"
        )

    @property
    def get_pair(self):
        """
        Returns the pair relationship. If the pair relationship does
        not exists, None value will be returned.
        :return:  ClientScheduledStatus
        """
        try:
            return self.pair or self.my_pair
        except ClientScheduledStatus.DoesNotExist:
            return None

    def process(self):
        """Process a scheduled change if valid."""
        if self.is_valid():
            # Update the client status
            self.client.status = self.status_to
            self.client.save()
            # Update the instance status
            self.operation_status = self.PROCESSED
            self.save()
            # Add note to client
            self.add_note_to_client()
            return True
        else:
            self.operation_status = self.ERROR
            self.save()
            return False

    def is_valid(self):
        """Returns True if a scheduled change must be applied."""
        return (
            self.client.status == self.status_from
            and self.operation_status == self.TOBEPROCESSED
        )

    def add_note_to_client(self, author=None):
        note = Note(
            note=self,
            author=author,
            client=self.client,
        )
        note.save()

    @property
    def needs_attention(self):
        """
        Return True if the status is ERROR or the scheduled date has passed.
        """
        return (self.operation_status == self.ERROR) or (
            self.change_date <= timezone.datetime.date(timezone.datetime.today())
        )


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


class Relationship(models.Model):
    REFERENT = "referent"
    EMERGENCY = "emergency"
    TYPE_CHOICES = (
        (REFERENT, _("Referent")),
        (EMERGENCY, _("Emergency")),
    )
    TYPE_CHOICES_DICT = dict(TYPE_CHOICES)

    member = models.ForeignKey("member.Member", on_delete=models.CASCADE)
    client = models.ForeignKey("member.Client", on_delete=models.CASCADE)
    nature = models.CharField(max_length=100)
    # Relationship.type is linked with a forms.MultipleChoiceField
    type = JSONField(default=[], blank=True)
    extra_fields = JSONField(default={}, blank=True)
    remark = models.TextField(blank=True)

    def __str__(self):
        return (
            f"{self.member.firstname} {self.member.lastname} is "
            f"{self.get_type_display()} member of {self.client.member.firstname} "
            f"{self.client.member.lastname}"
        )

    def get_type_display(self):
        return "+".join(
            map(
                force_text,
                list(map(lambda t: self.TYPE_CHOICES_DICT[t], self.type))
                or ([_("Unknown type")]),
            )
        )

    class Meta:
        verbose_name_plural = _("relationships")
        unique_together = ("client", "member")

    def is_referent(self):
        return self.REFERENT in self.type

    def is_emergency(self):
        return self.EMERGENCY in self.type


class Option(models.Model):
    class Meta:
        verbose_name_plural = _("options")

    # Information about options added to the meal
    name = models.CharField(max_length=50, verbose_name=_("name"))

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        null=True,
    )

    option_group = models.CharField(
        max_length=100, choices=OPTION_GROUP_CHOICES, verbose_name=_("option group")
    )

    def __str__(self):
        return self.name


class Client_option(models.Model):
    client = models.ForeignKey(
        "member.Client", verbose_name=_("client"), on_delete=models.CASCADE
    )

    option = models.ForeignKey(
        "member.option", verbose_name=_("option"), on_delete=models.CASCADE
    )

    value = models.CharField(max_length=255, null=True, verbose_name=_("value"))
    #  value contents depends on option_group of option occurence pointed to:
    #    if option_group = main_dish_size : 'Regular' or 'Large'
    #    if option_group = dish : qty Monday to Sunday ex. '1110120'
    #    if option_group = preparation : Null
    #    if option_group = other_order_item : No occurrence of Client_option

    def __str__(self):
        return (
            f"{self.client.member.firstname} {self.client.member.lastname} <has> "
            f"{self.option.name}"
        )


class Restriction(models.Model):
    client = models.ForeignKey(
        "member.Client",
        verbose_name=_("client"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    restricted_item = models.ForeignKey(
        "meal.Restricted_item",
        verbose_name=_("restricted item"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return (
            f"{self.client.member.firstname} {self.client.member.lastname} "
            f"<restricts> {self.restricted_item.name}"
        )


class Client_avoid_ingredient(models.Model):
    client = models.ForeignKey(
        "member.Client",
        verbose_name=_("client"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    ingredient = models.ForeignKey(
        "meal.Ingredient",
        verbose_name=_("ingredient"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return (
            f"{self.client.member.firstname} {self.client.member.lastname} "
            f"<has> {self.ingredient.name}"
        )


class Client_avoid_component(models.Model):
    client = models.ForeignKey(
        "member.Client",
        verbose_name=_("client"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    component = models.ForeignKey(
        "meal.Component",
        verbose_name=_("component"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return (
            f"{self.client.member.firstname} {self.client.member.lastname} "
            f"<has> {self.component.name}"
        )
