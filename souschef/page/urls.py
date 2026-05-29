from django.contrib.auth import views as auth_views
from django.urls import path
from django.utils.translation import gettext_lazy as _

from souschef.page import views

app_name = "page"

urlpatterns = [
    path(_("home"), views.HomeView.as_view(), name="home"),
    path(_("login"), views.CustomLoginView.as_view(), name="login"),
    path(
        _("logout"),
        auth_views.LogoutView.as_view(),
        {"next_page": "/"},
        name="logout",
    ),
]
