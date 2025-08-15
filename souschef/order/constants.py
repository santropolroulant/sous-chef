from django.utils.translation import ugettext_lazy as _

ORDER_STATUS = (
    ("O", _("Ordered")),
    ("D", _("Delivered")),
    ("N", _("No Charge")),
    ("C", _("Cancelled")),
    ("B", _("Billed")),
    ("P", _("Paid")),
)

ORDER_STATUS_ORDERED = ORDER_STATUS[0][0]
ORDER_STATUS_DELIVERED = ORDER_STATUS[1][0]
ORDER_STATUS_NO_CHARGE = ORDER_STATUS[2][0]
ORDER_STATUS_CANCELLED = ORDER_STATUS[3][0]

SIZE_CHOICES = (
    ("", ""),
    ("R", _("Regular")),
    ("L", _("Large")),
)

SIZE_CHOICES_REGULAR = SIZE_CHOICES[1][0]
SIZE_CHOICES_LARGE = SIZE_CHOICES[2][0]

ORDER_ITEM_TYPE_CHOICES = (
    ("meal_component", _("Meal component (main dish, vegetable, side dish, seasonal)")),
    ("delivery", _("Delivery (general store item, invitation, ...)")),
    ("pickup", _("Pickup (payment)")),
    ("visit", _("Visit")),
)

ORDER_ITEM_TYPE_CHOICES_COMPONENT = ORDER_ITEM_TYPE_CHOICES[0][0]
