from django.urls import path
from django.utils.translation import gettext_lazy as _

from souschef.delivery.views import (
    CreateDelivery,
    DeliveryRouteSheet,
    EditDeliveryRoute,
    KitchenCount,
    MealInformation,
    RefreshOrderView,
    ReviewOrders,
    RoutesInformation,
)

app_name = "delivery"

urlpatterns = [
    path(_("order/"), ReviewOrders.as_view(), name="order"),
    path(_("meal/"), MealInformation.as_view(), name="meal"),
    path(_("meal/<int:id>/"), MealInformation.as_view(), name="meal_id"),
    path(_("routes/"), RoutesInformation.as_view(), name="routes"),
    path(
        _("route/<int:pk>/"),
        EditDeliveryRoute.as_view(),
        name="edit_delivery_route",
    ),
    path(
        _("route/<int:pk>/create/"),
        CreateDelivery.as_view(),
        name="create_delivery",
    ),
    path(_("kitchen_count/"), KitchenCount.as_view(), name="kitchen_count"),
    path(
        _("route_sheet/<int:pk>/"),
        DeliveryRouteSheet.as_view(),
        name="route_sheet",
    ),
    path(_("refresh_orders/"), RefreshOrderView.as_view(), name="refresh_orders"),
]
