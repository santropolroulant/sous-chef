import datetime
import random

import factory
from factory.django import DjangoModelFactory
from faker import Factory as FakerFactory

from souschef.member.factories import ClientFactory
from souschef.order.constants import ORDER_ITEM_TYPE_CHOICES, ORDER_STATUS, SIZE_CHOICES
from souschef.order.models import (
    Order,
    Order_item,
)

fake = FakerFactory.create()


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    creation_date = factory.LazyFunction(
        lambda: datetime.datetime.now(datetime.UTC)
    )
    delivery_date = factory.Faker("date_time_between", start_date="-1y", end_date="+1y")
    client = factory.SubFactory(ClientFactory)
    status = factory.LazyAttribute(lambda x: random.choice(ORDER_STATUS)[0])

    order_item = factory.RelatedFactory(
        "order.factories.OrderItemFactory",
        "order",
        price="5",
        billable_flag=True,
    )


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = Order_item

    order = factory.SubFactory(OrderFactory)

    price = factory.Faker("random_int", min=0, max=50)

    billable_flag = factory.LazyAttribute(lambda x: random.choice([True, False]))

    size = factory.LazyAttribute(lambda x: random.choice(SIZE_CHOICES)[0])

    order_item_type = factory.LazyAttribute(
        lambda x: random.choice(ORDER_ITEM_TYPE_CHOICES)[0]
    )

    remark = factory.Faker("sentence", nb_words=6, variable_nb_words=True)

    total_quantity = factory.Faker("random_digit")
