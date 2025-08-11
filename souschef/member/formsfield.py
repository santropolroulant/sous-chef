import re

from django import forms
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

phone_digits_re = re.compile(r"^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$")


class CAPhoneNumberField(Field):
    """
    Canadian phone number form field.
    Comes from previous version of localflavor.ca.forms.CAPhoneNumberField.
    """

    default_error_messages = {
        "invalid": _("Phone numbers must be in XXX-XXX-XXXX format."),
    }

    def clean(self, value):
        super().clean(value)

        if value in EMPTY_VALUES:
            return ""

        value = re.sub(r"(\(|\)|\s+)", "", force_text(value))

        m = phone_digits_re.search(value)

        if m:
            return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))

        raise ValidationError(self.error_messages["invalid"])


class CAPhoneNumberExtField(CAPhoneNumberField):
    """Canadian phone number form field."""

    phone_digits_re = re.compile(r"^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$")
    phone_digits_with_ext = re.compile(
        r"^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})#?(\d*)$"
    )

    default_error_messages = {
        "invalid": _("Phone numbers must be in XXX-XXX-XXXX # XXXXX format."),
    }

    def clean(self, value):
        try:
            return super().clean(value)
        except forms.ValidationError as error:
            value = re.sub(r"(\(|\)|\s+)", "", force_text(value))
            m = self.phone_digits_with_ext.search(value)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)} #{m.group(4)}"
            raise error
