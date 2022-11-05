# coding=utf-8
import random
from datetime import date

import factory
from faker import Factory as FakerFactory

from souschef.member.factories import ClientFactory
from souschef.order.models import (
    ORDER_ITEM_TYPE_CHOICES,
    ORDER_STATUS,
    SIZE_CHOICES,
    Order,
    Order_item,
)

fake = FakerFactory.create()


class OrderFactory(factory.DjangoModelFactory):
    class Meta:
        model = Order

    creation_date = date.today()

    delivery_date = factory.LazyAttribute(
        lambda x: fake.date_time_between(start_date="-1y", end_date="+1y", tzinfo=None)
    )

    status = factory.LazyAttribute(lambda x: random.choice(ORDER_STATUS)[0])

    client = factory.SubFactory(ClientFactory)

    order_item = factory.RelatedFactory(
        "order.factories.OrderItemFactory",
        "order",
        price="5",
        billable_flag=True,
    )


class OrderItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = Order_item

    order = factory.SubFactory(OrderFactory)

    price = fake.random_int(min=0, max=50)

    billable_flag = factory.LazyAttribute(lambda x: random.choice([True, False]))

    size = factory.LazyAttribute(lambda x: random.choice(SIZE_CHOICES)[0])

    order_item_type = factory.LazyAttribute(
        lambda x: random.choice(ORDER_ITEM_TYPE_CHOICES)[0]
    )

    remark = fake.sentence(nb_words=6, variable_nb_words=True)

    total_quantity = fake.random_digit()
