import datetime
import os

import pkg_resources
from django.conf import settings

from souschef.member.models import (
    Client,
    Route,
)
from souschef.note.models import (
    Note,
    NoteFilter,
)
from souschef.order.constants import ORDER_STATUS_ORDERED
from souschef.order.models import Order


def get_sous_chef_version():
    if os.environ.get("CI") == "1":
        return "dev"

    return pkg_resources.require("souschef")[0].version


def total(request):
    """Passing entities total into RequestContext."""

    clients = Client.objects.count()
    orders = Order.objects.count()
    routes = Route.objects.count()
    # Only unread messages
    notes = Note.unread.count()

    COMMON_CONTEXT = {
        "CLIENTS_TOTAL": clients,
        "ORDERS_TOTAL": orders,
        "ROUTES_TOTAL": routes,
        "NOTES_TOTAL": notes,
        # This is pretty bad separation of concert to puth the following here
        # But since there is no actual view associated with menu.html (it's
        # just included is base.html, this is the most DRY way I found
        "CLIENT_FILTER_DEFAULT_STATUS": Client.ACTIVE,
        "ORDER_FILTER_DEFAULT_STATUS": ORDER_STATUS_ORDERED,
        "ORDER_FILTER_DEFAULT_DATE": datetime.datetime.now(),
        "NOTE_FILTER_DEFAULT_IS_READ": NoteFilter.NOTE_STATUS_UNREAD,
        "SC_ENVIRONMENT_NAME": settings.SOUSCHEF_ENVIRONMENT_NAME,
        "SC_VERSION": get_sous_chef_version(),
        "GIT_HEAD": settings.GIT_HEAD,
        "GIT_TAG": settings.GIT_TAG,
    }

    return COMMON_CONTEXT
