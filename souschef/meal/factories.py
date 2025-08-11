import random

import factory
from factory.django import DjangoModelFactory
from faker import Factory as FakerFactory

from souschef.meal.models import (
    COMPONENT_GROUP_CHOICES,
    INGREDIENT_GROUP_CHOICES,
    RESTRICTED_ITEM_GROUP_CHOICES,
    Component,
    Component_ingredient,
    Incompatibility,
    Ingredient,
    Menu,
    Menu_component,
    Restricted_item,
)

fake = FakerFactory.create()


class IngredientFactory(DjangoModelFactory):
    class Meta:
        model = Ingredient

    name = factory.Faker("word")

    description = factory.Faker("sentence", nb_words=10, variable_nb_words=True)

    ingredient_group = factory.LazyAttribute(
        lambda x: random.choice(INGREDIENT_GROUP_CHOICES)[0]
    )


class ComponentFactory(DjangoModelFactory):
    class Meta:
        model = Component

    name = factory.Faker("word")

    description = factory.Faker("sentence", nb_words=10, variable_nb_words=True)

    component_group = factory.LazyAttribute(
        lambda x: random.choice(COMPONENT_GROUP_CHOICES)[0]
    )


class ComponentIngredientFactory(DjangoModelFactory):
    class Meta:
        model = Component_ingredient

    component = factory.SubFactory(ComponentFactory)

    ingredient = factory.SubFactory(IngredientFactory)


class RestrictedItemFactory(DjangoModelFactory):
    class Meta:
        model = Restricted_item

    name = factory.Faker("word")

    description = factory.Faker("sentence", nb_words=10, variable_nb_words=True)

    restricted_item_group = factory.LazyAttribute(
        lambda x: random.choice(RESTRICTED_ITEM_GROUP_CHOICES)[0]
    )


class IncompatibilityFactory(DjangoModelFactory):
    class Meta:
        model = Incompatibility

    restricted_item = factory.SubFactory(RestrictedItemFactory)

    ingredient = factory.SubFactory(Ingredient)


class MenuFactory(DjangoModelFactory):
    class Meta:
        model = Menu

    date = factory.Faker("date_between", start_date="-1y", end_date="+1y")

    menu_component = factory.RelatedFactory(
        "meal.factories.MenuComponentFactory", "menu"
    )


class MenuComponentFactory(DjangoModelFactory):
    class Meta:
        model = Menu_component

    menu = factory.SubFactory(MenuFactory)

    component = factory.SubFactory(ComponentFactory)
