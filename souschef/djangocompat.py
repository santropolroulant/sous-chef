from django.urls.base import lazy
from django.utils.encoding import force_str


def _string_concat(*strings):
    """
    Lazy variant of string concatenation, needed for translations that are
    constructed from multiple parts.
    From https://docs.djangoproject.com/en/1.8/_modules/django/utils/translation/
    """
    return "".join(force_str(s) for s in strings)


string_concat = lazy(_string_concat, str)
