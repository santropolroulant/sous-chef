from typing import Tuple

from django.utils.translation import ugettext_lazy as _

from souschef.member.types import RateType

HOME = "Home phone"
CELL = "Cell phone"
WORK = "Work phone"
EMAIL = "Email"

GENDER_CHOICES = (
    ("F", _("Female")),
    ("M", _("Male")),
    ("O", _("Other")),
)

CONTACT_TYPE_CHOICES = (
    (HOME, HOME),
    (CELL, CELL),
    (WORK, WORK),
    (EMAIL, EMAIL),
)

RATE_TYPE: Tuple[Tuple[RateType, str], ...] = (
    ("default", _("Default")),
    ("low income", _("Low income")),
    ("solidary", _("Solidary")),
)

RATE_TYPE_DEFAULT = RATE_TYPE[0][0]
RATE_TYPE_LOW_INCOME = RATE_TYPE[1][0]
RATE_TYPE_SOLIDARY = RATE_TYPE[2][0]

PAYMENT_TYPE = (
    (" ", _("----")),
    ("3rd", "3rd Party"),
    ("credit", "Carte de crédit"),
    ("cash", "Cash"),
    ("cheque", "Chèque"),
    ("creditphon", "Credit téléphone"),
    ("eft", "EFT"),
    ("free", "Gratuité"),
    ("etransfert", "Interac"),
)

MAILING_TYPE = (
    (" ", _("----")),
    ("email", "Email"),
    ("paper", "Paper"),
)

DELIVERY_TYPE = (
    ("O", _("Ongoing")),
    ("E", _("Episodic")),
)

OPTION_GROUP_CHOICES = (
    ("main dish size", _("Main dish size")),
    ("dish", _("Dish")),
    ("preparation", _("Preparation")),
    ("other order item", _("Other order item")),
)

OPTION_GROUP_CHOICES_PREPARATION = OPTION_GROUP_CHOICES[2][0]

DAYS_OF_WEEK = (
    ("monday", _("Monday")),
    ("tuesday", _("Tuesday")),
    ("wednesday", _("Wednesday")),
    ("thursday", _("Thursday")),
    ("friday", _("Friday")),
    ("saturday", _("Saturday")),
    ("sunday", _("Sunday")),
)

ROUTE_VEHICLES = (
    # Vehicles should be supported by mapbox.
    ("cycling", _("Cycling")),
    ("walking", _("Walking")),
    ("driving", _("Driving")),
)

DEFAULT_VEHICLE = ROUTE_VEHICLES[0][0]
