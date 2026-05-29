from django.urls import path
from django.utils.translation import gettext_lazy as _

from souschef.billing.views import (
    BillingAdd,
    BillingCreate,
    BillingDelete,
    BillingList,
    BillingOrdersView,
    BillingSummaryView,
)

app_name = "billing"

urlpatterns = [
    path(_("list/"), BillingList.as_view(), name="list"),
    path(_("create/"), BillingCreate.as_view(), name="create"),
    path(_("add/"), BillingAdd.as_view(), name="add"),
    path(_("view/<int:pk>/"), BillingSummaryView.as_view(), name="view"),
    path(
        _("view/<int:pk>/orders/"),
        BillingOrdersView.as_view(),
        name="view_orders",
    ),
    path(_("delete/<int:pk>/"), BillingDelete.as_view(), name="delete"),
]
