from django.urls import path
from django.utils.translation import gettext_lazy as _

from souschef.order.views import (
    CancelOrder,
    CreateDeleteOrderClientBill,
    CreateOrder,
    CreateOrdersBatch,
    DeleteOrder,
    OrderDetail,
    OrderList,
    UpdateOrder,
    UpdateOrderStatus,
)

app_name = "order"

urlpatterns = [
    path(_("list/"), OrderList.as_view(), name="list"),
    path(_("view/<int:pk>/"), OrderDetail.as_view(), name="view"),
    path(_("create/"), CreateOrder.as_view(), name="create"),
    # Multiple orders as once
    path(_("create/batch"), CreateOrdersBatch.as_view(), name="create_batch"),
    path(_("update/<int:pk>/"), UpdateOrder.as_view(), name="update"),
    path(
        _("update/<int:pk>/status"),
        UpdateOrderStatus.as_view(),
        name="update_status",
    ),
    path(
        _("update/<int:pk>/client_bill"),
        CreateDeleteOrderClientBill.as_view(),
        name="update_client_bill",
    ),
    path(_("cancel/<int:pk>/"), CancelOrder.as_view(), name="cancel"),
    path(_("delete/<int:pk>/"), DeleteOrder.as_view(), name="delete"),
]
