import random

import factory
from factory.django import DjangoModelFactory

from souschef.meal.constants import COMPONENT_GROUP_CHOICES
from souschef.member.constants import (
    DAYS_OF_WEEK,
    DELIVERY_TYPE,
    GENDER_CHOICES,
    MAILING_TYPE,
    PAYMENT_TYPE,
    RATE_TYPE,
)
from souschef.member.models import (
    Address,
    Client,
    ClientScheduledStatus,
    Contact,
    DeliveryHistory,
    Member,
    Relationship,
    Route,
)


class AddressFactory(DjangoModelFactory):
    class Meta:
        model = Address

    street = factory.Faker("street_address")
    apartment = factory.Faker("random_number")
    city = "Montreal"
    postal_code = factory.Faker("postalcode", locale="en_CA")
    latitude = factory.LazyAttribute(lambda x: random.choice(["75.0", "75.1", "75.2"]))
    longitude = factory.LazyAttribute(lambda x: random.choice(["40.2", "40.1", "40.0"]))


class MemberFactory(DjangoModelFactory):
    class Meta:
        model = Member

    firstname = factory.Faker("first_name")
    lastname = factory.Faker("last_name")

    address = factory.SubFactory(AddressFactory)
    work_information = factory.Faker("company")
    contact = factory.RelatedFactory("member.factories.ContactFactory", "member")


class RouteFactory(DjangoModelFactory):
    class Meta:
        model = Route

    name = factory.Faker("name")


class DeliveryHistoryFactory(DjangoModelFactory):
    class Meta:
        model = DeliveryHistory


def generate_json():
    json = {}
    for day, _translation in DAYS_OF_WEEK:
        json[f"size_{day}"] = random.choice(["L", "R"])
        for meal, _Meal in COMPONENT_GROUP_CHOICES:
            json[f"{meal}_{day}_quantity"] = random.choice([0, 1])
    return json


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = Client

    member = factory.SubFactory(MemberFactory)
    billing_member = member
    billing_payment_type = factory.LazyAttribute(
        lambda x: random.choice(PAYMENT_TYPE)[0]
    )
    billing_mailing_type = factory.LazyAttribute(
        lambda x: random.choice(MAILING_TYPE)[0]
    )
    rate_type = factory.LazyAttribute(lambda x: random.choice(RATE_TYPE)[0])
    member = member
    status = factory.LazyAttribute(lambda x: random.choice(Client.CLIENT_STATUS)[0])
    language = factory.LazyAttribute(lambda x: random.choice(Client.LANGUAGES)[0])
    alert = factory.Faker("sentence")
    delivery_type = factory.LazyAttribute(lambda x: random.choice(DELIVERY_TYPE)[0])
    gender = factory.LazyAttribute(lambda x: random.choice(GENDER_CHOICES)[0])
    birthdate = factory.Faker("date")
    route = factory.LazyAttribute(lambda x: random.choice(Route.objects.all()))

    delivery_note = factory.Faker("sentence")

    meal_default_week = factory.LazyAttribute(lambda x: generate_json())


def random_combination(iterable, r):
    """
    Random selection from itertools.combinations(iterable, r)
    From Python docs (itertools)
    """
    pool = tuple(iterable)
    n = len(pool)
    indices = sorted(random.sample(range(n), r))
    return tuple(pool[i] for i in indices)


class RelationshipFactory(DjangoModelFactory):
    class Meta:
        model = Relationship

    client = factory.SubFactory(ClientFactory)
    member = factory.SubFactory(MemberFactory)
    nature = factory.LazyAttribute(
        lambda x: random.choice(["friends", "family", "coworkers"])
    )
    type = factory.LazyAttribute(
        lambda x: list(
            random_combination(
                map(lambda tup: tup[0], Relationship.TYPE_CHOICES),
                random.randint(0, len(Relationship.TYPE_CHOICES)),
            )
        )
    )
    extra_fields = factory.LazyAttribute(lambda x: {})
    remark = factory.Faker("sentence")


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = Contact

    type = "Home phone"
    value = factory.Sequence(lambda n: "514-555-%04d" % n)
    member = factory.SubFactory(MemberFactory)


class ClientScheduledStatusFactory(DjangoModelFactory):
    class Meta:
        model = ClientScheduledStatus

    client = factory.SubFactory(ClientFactory)
    status_from = factory.LazyAttribute(
        lambda x: random.choice(Client.CLIENT_STATUS)[0]
    )
    status_to = factory.LazyAttribute(lambda x: random.choice(Client.CLIENT_STATUS)[0])
    reason = factory.Faker("sentence")
    change_date = factory.Faker("date")
    change_state = factory.LazyAttribute(
        lambda x: random.choice(ClientScheduledStatus.CHANGE_STATUS)[0]
    )
    operation_status = ClientScheduledStatus.TOBEPROCESSED
