from django.urls import path
from django.utils.translation import gettext_lazy as _

from souschef.djangocompat import string_concat
from souschef.member.forms import (
    ClientAddressInformation,
    ClientBasicInformation,
    ClientPaymentInformation,
    ClientRestrictionsInformation,
)
from souschef.member.formsets import CreateRelationshipFormset
from souschef.member.views import (
    ClientAllergiesView,
    ClientInfoView,
    ClientList,
    ClientOrderList,
    ClientPaymentView,
    ClientStatusScheduler,
    ClientStatusSchedulerDeleteView,
    ClientStatusSchedulerReschedule,
    ClientStatusView,
    ClientUpdateAddressInformation,
    ClientUpdateBasicInformation,
    ClientUpdateDietaryRestriction,
    ClientUpdatePaymentInformation,
    ClientUpdateRelationshipsInformation,
    ClientWizard,
    DeleteClientOption,
    DeleteComponentToAvoid,
    DeleteIngredientToAvoid,
    DeleteRestriction,
    DeliveryHistoryDetailView,
    RouteDetailView,
    RouteEditView,
    RouteListView,
    SearchMembers,
    geolocateAddress,
    get_minimised_euclidean_distances_route_sequence,
)
from souschef.note.views import (
    ClientNoteList,
    ClientNoteListAdd,
)

app_name = "member"

member_forms = (
    {
        "name": "basic_information",
        "step_url": _("basic_information"),
        "create_form": ClientBasicInformation,
        "update_form": ClientUpdateBasicInformation,
    },
    {
        "name": "address_information",
        "step_url": _("address_information"),
        "create_form": ClientAddressInformation,
        "update_form": ClientUpdateAddressInformation,
    },
    {
        "name": "relationships",
        "step_url": _("relationships"),
        "create_form": CreateRelationshipFormset,
        "update_form": ClientUpdateRelationshipsInformation,
    },
    {
        "name": "payment_information",
        "step_url": _("payment_information"),
        "create_form": ClientPaymentInformation,
        "update_form": ClientUpdatePaymentInformation,
    },
    {
        "name": "dietary_restriction",
        "step_url": _("dietary_restriction"),
        "create_form": ClientRestrictionsInformation,
        "update_form": ClientUpdateDietaryRestriction,
    },
)

member_wizard = ClientWizard.as_view(
    list(map(lambda d: (d["name"], d["create_form"]), member_forms)),
    i18n_url_names=list(map(lambda d: (d["name"], d["step_url"]), member_forms)),
    url_name="member:member_step",
)


urlpatterns = [
    path(_("create/"), member_wizard, name="member_step"),
    path(_("create/<str:step>/"), member_wizard, name="member_step"),
    path(_("list/"), ClientList.as_view(), name="list"),
    path(_("search/"), SearchMembers.as_view(), name="search"),
    path(_("view/<int:pk>/orders"), ClientOrderList.as_view(), name="list_orders"),
    path(
        _("view/<int:pk>/information"),
        ClientInfoView.as_view(),
        name="client_information",
    ),
    path(
        _("view/<int:pk>/billing"),
        ClientPaymentView.as_view(),
        name="client_payment",
    ),
    path(
        _("view/<int:pk>/preferences"),
        ClientAllergiesView.as_view(),
        name="client_allergies",
    ),
    path(_("view/<int:pk>/notes"), ClientNoteList.as_view(), name="client_notes"),
    path(
        _("view/<int:pk>/notes/add"),
        ClientNoteListAdd.as_view(),
        name="client_notes_add",
    ),
    path(_("geolocateAddress/"), geolocateAddress, name="geolocateAddress"),
    path(
        _("view/<int:pk>/status"),
        ClientStatusView.as_view(),
        name="client_status",
    ),
    path(
        _("client/<int:pk>/status/scheduler"),
        ClientStatusScheduler.as_view(),
        name="clientStatusScheduler",
    ),
    path(
        _("client/<int:pk>/status/scheduler/reschedule/<int:scheduled_status_1_pk>/"),
        ClientStatusSchedulerReschedule.as_view(),
        name="clientStatusSchedulerRescheduleOneStatus",
    ),
    path(
        _(
            "client/<int:pk>/status/scheduler/reschedule/"
            "<int:scheduled_status_1_pk>"
            "/<int:scheduled_status_2_pk>/"
        ),
        ClientStatusSchedulerReschedule.as_view(),
        name="clientStatusSchedulerRescheduleTwoStatus",
    ),
    path(
        "status/<int:pk>/delete",
        ClientStatusSchedulerDeleteView.as_view(),
        name="delete_status",
    ),
    path(
        _("restriction/<int:pk>/delete/"),
        DeleteRestriction.as_view(),
        name="restriction_delete",
    ),
    path(
        _("client_option/<int:pk>/delete/"),
        DeleteClientOption.as_view(),
        name="client_option_delete",
    ),
    path(
        _("ingredient_to_avoid/<int:pk>/delete/"),
        DeleteIngredientToAvoid.as_view(),
        name="ingredient_to_avoid_delete",
    ),
    path(
        _("component_to_avoid/<int:pk>/delete/"),
        DeleteComponentToAvoid.as_view(),
        name="component_to_avoid_delete",
    ),
    path(_("routes/"), RouteListView.as_view(), name="route_list"),
    path(_("route/<int:pk>/"), RouteDetailView.as_view(), name="route_detail"),
    path(_("route/<int:pk>/edit/"), RouteEditView.as_view(), name="route_edit"),
    path(
        _("route/<int:pk>/optimised_sequence/"),
        get_minimised_euclidean_distances_route_sequence,
        name="route_get_optimised_sequence",
    ),
    path(
        _("route/<int:route_pk>/<str:date>/"),
        DeliveryHistoryDetailView.as_view(),
        name="delivery_history_detail",
    ),
]


# Handle client update forms URL
for d in member_forms:
    urlpatterns.append(
        path(
            string_concat(_("<int:pk>/update/"), d["step_url"], "/"),
            d["update_form"].as_view(),
            name="member_update_" + d["name"],
        )
    )
