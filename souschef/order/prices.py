from decimal import Decimal

from typing_extensions import Literal

from souschef.member.constants import (
    RATE_TYPE_DEFAULT,
    RATE_TYPE_LOW_INCOME,
    RATE_TYPE_SOLIDARY,
)
from souschef.member.types import RateType

MAIN_PRICE_DEFAULT = Decimal("6.00")
MAIN_PRICE_LOW_INCOME = Decimal("4.50")
MAIN_PRICE_SOLIDARY = Decimal("3.50")

SIDE_PRICE_DEFAULT = Decimal("1.00")
SIDE_PRICE_LOW_INCOME = Decimal("0.75")
SIDE_PRICE_SOLIDARY = Decimal("0.50")

MealSize = Literal["R", "L"]


def get_main_dish_unit_price(*, rate_type: RateType, size: MealSize) -> Decimal:
    if rate_type == RATE_TYPE_DEFAULT:
        main_price = MAIN_PRICE_DEFAULT
    elif rate_type == RATE_TYPE_LOW_INCOME:
        main_price = MAIN_PRICE_LOW_INCOME
    elif rate_type == RATE_TYPE_SOLIDARY:
        main_price = MAIN_PRICE_SOLIDARY
    else:
        raise Exception(f"Unknown rate_type: {rate_type}")

    side_price = get_side_unit_price(rate_type=rate_type)

    if size == "R":
        return main_price
    elif size == "L":
        return main_price + side_price
    else:
        raise Exception(f"Unknown size: {size}")


def get_side_unit_price(*, rate_type: str) -> Decimal:
    if rate_type == RATE_TYPE_DEFAULT:
        return SIDE_PRICE_DEFAULT
    elif rate_type == RATE_TYPE_LOW_INCOME:
        return SIDE_PRICE_LOW_INCOME
    elif rate_type == RATE_TYPE_SOLIDARY:
        return SIDE_PRICE_SOLIDARY
    else:
        raise Exception(f"Unknown rate_type: {rate_type}")
