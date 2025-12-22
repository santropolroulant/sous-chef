from collections import defaultdict
from typing import TypedDict

from souschef.member.types import RateType


class RegularLargeDict(TypedDict):
    R: int
    L: int


class ClientStatistics(TypedDict):
    id: int
    firstname: str
    lastname: str
    payment_type_display: str
    mailing_type_display: str
    rate_type: RateType
    rate_type_display: str
    total_main_dishes: RegularLargeDict
    total_billable_extras: int
    total_amount: int
    delivery_type_verbose: str
    number_of_deliveries_in_month: int


class PaymentTypeStatistics(TypedDict):
    total_main_dishes: RegularLargeDict
    total_billable_extras: int
    total_amount: int
    total_deliveries: int
    clients: list[ClientStatistics]


type BillingPaymentType = str | None


class BillingSummary(TypedDict):
    total_main_dishes: RegularLargeDict
    total_billable_extras: int
    total_amount: int
    total_deliveries: int
    payment_types_dict: defaultdict[BillingPaymentType, PaymentTypeStatistics]
    payment_types: list[tuple[BillingPaymentType, PaymentTypeStatistics]]
