from django.utils.translation import ugettext_lazy as _

COMPONENT_GROUP_CHOICES = (
    ("main_dish", _("Main Dish")),
    ("dessert", _("Dessert")),
    ("diabetic", _("Diabetic")),
    ("fruit_salad", _("Fruit Salad")),
    ("green_salad", _("Green Salad")),
    ("pudding", _("Pudding")),
    ("compote", _("Compote")),
    ("sides", _("Sides")),
)

COMPONENT_GROUP_CHOICES_MAIN_DISH = COMPONENT_GROUP_CHOICES[0][0]
COMPONENT_GROUP_CHOICES_SIDES = COMPONENT_GROUP_CHOICES[7][0]

INGREDIENT_GROUP_CHOICES = (
    ("meat", _("Meat")),
    ("dairy", _("Dairy")),
    ("fish", _("Fish")),
    ("seafood", _("Seafood")),
    ("veggies_and_fruits", _("Veggies and fruits")),
    ("legumineuse", _("Legumineuse")),
    ("grains", _("Grains")),
    ("fresh_herbs", _("Fresh herbs")),
    ("spices", _("Spices")),
    ("dry_and_canned_goods", _("Dry and canned goods")),
    ("oils_and_sauces", _("Oils and sauces")),
)

RESTRICTED_ITEM_GROUP_CHOICES = (
    ("meat", _("Meat")),
    ("vegetables", _("Vegetables")),
    ("seafood", _("Seafood")),
    ("seeds and nuts", _("Seeds and nuts")),
    ("other", _("Other")),
)
