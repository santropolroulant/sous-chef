from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _

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
    url(_(r"^order/$"), ReviewOrders.as_view(), name="order"),
    url(_(r"^meal/$"), MealInformation.as_view(), name="meal"),
    url(_(r"^meal/(?P<id>\d+)/$"), MealInformation.as_view(), name="meal_id"),
    url(_(r"^routes/$"), RoutesInformation.as_view(), name="routes"),
    url(
        _(r"^route/(?P<pk>\d+)/$"),
        EditDeliveryRoute.as_view(),
        name="edit_delivery_route",
    ),
    url(
        _(r"^route/(?P<pk>\d+)/create/$"),
        CreateDelivery.as_view(),
        name="create_delivery",
    ),
    url(_(r"^kitchen_count/$"), KitchenCount.as_view(), name="kitchen_count"),
    url(
        _(r"^route_sheet/(?P<pk>\d+)/$"),
        DeliveryRouteSheet.as_view(),
        name="route_sheet",
    ),
    url(_(r"^refresh_orders/$"), RefreshOrderView.as_view(), name="refresh_orders"),
]
