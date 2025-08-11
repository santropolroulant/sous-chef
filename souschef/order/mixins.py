from django.http import JsonResponse


class FormInvalidAjaxableResponseMixin:
    """
    Only ajaxable when the form is invalid: returning errors.
    """

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(form.errors, status=400)
        else:
            return response


class FormValidAjaxableResponseMixin:
    """
    Only ajaxable when the form is valid: returning pk.
    """

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "pk": self.object.pk,
            }
            return JsonResponse(data)
        else:
            return response


class AjaxableResponseMixin(
    FormInvalidAjaxableResponseMixin, FormValidAjaxableResponseMixin
):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    https://docs.djangoproject.com/ja/1.9/topics/class-based-views/generic-editing/#ajax-example
    """

    pass
