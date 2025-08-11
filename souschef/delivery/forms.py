from django import forms
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from souschef.meal.constants import COMPONENT_GROUP_CHOICES_MAIN_DISH
from souschef.meal.models import (
    Component,
    Ingredient,
)


class DishIngredientsForm(forms.Form):
    maindish = forms.ModelChoiceField(
        label=_("Today's main dish:"),
        queryset=Component.objects.order_by(Lower("name")).filter(
            component_group=COMPONENT_GROUP_CHOICES_MAIN_DISH
        ),
        widget=forms.Select(attrs={"class": "ui dropdown maindish"}),
    )

    ingredients = forms.ModelMultipleChoiceField(
        label=_("Select main dish ingredients:"),
        queryset=Ingredient.objects.order_by(Lower("name")).all(),
        widget=forms.SelectMultiple(
            attrs={"class": "ui fluid search dropdown mainingredients"}
        ),
        required=False,
    )

    sides_ingredients = forms.ModelMultipleChoiceField(
        label=_("Select sides ingredients:"),
        queryset=Ingredient.objects.order_by(Lower("name")).all(),
        widget=forms.SelectMultiple(
            attrs={"class": "ui fluid search dropdown sidesingredients"}
        ),
        required=False,
    )

    def clean_sides_ingredients(self):
        data = self.cleaned_data["sides_ingredients"]
        if not data:
            raise forms.ValidationError(_("Please choose some Sides ingredients"))
        return data
