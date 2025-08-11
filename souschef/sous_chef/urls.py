"""sous-chef URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/

Examples:

Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf
    1. Import the include() function: from django.urls import path, include
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import (
    include,
    path,
)
from django.utils.translation import gettext_lazy as _

from souschef.page.views import HomeView

urlpatterns = i18n_patterns(
    path(_("admin/"), admin.site.urls),
    path(_("meal/"), include("souschef.meal.urls", namespace="meal")),
    path(_("member/"), include("souschef.member.urls", namespace="member")),
    path(
        _("notification/"),
        include("souschef.notification.urls", namespace="notification"),
    ),
    path(_("order/"), include("souschef.order.urls", namespace="order")),
    path("p/", include("souschef.page.urls", namespace="page")),
    path("", HomeView.as_view(), name="home"),
    path(_("delivery/"), include("souschef.delivery.urls", namespace="delivery")),
    path(_("note/"), include("souschef.note.urls", namespace="note")),
    path(_("billing/"), include("souschef.billing.urls", namespace="billing")),
    prefix_default_language=False,
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
