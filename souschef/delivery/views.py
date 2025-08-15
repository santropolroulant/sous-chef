from __future__ import annotations

import collections
import json
import os
import textwrap
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

import labels  # package pylabels
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.urls import (
    reverse,
    reverse_lazy,
)
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django_filters.views import FilterView
from reportlab.lib import colors as rl_colors
from reportlab.lib import enums as rl_enums
from reportlab.lib import pagesizes
from reportlab.lib.styles import ParagraphStyle as RLParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet as rl_getSampleStyleSheet
from reportlab.lib.units import inch as rl_inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak as RLPageBreak
from reportlab.platypus import Paragraph as RLParagraph
from reportlab.platypus import SimpleDocTemplate as RLSimpleDocTemplate
from reportlab.platypus import Spacer as RLSpacer
from reportlab.platypus import Table as RLTable
from reportlab.platypus import TableStyle as RLTableStyle

from souschef.delivery.meal_labels import MealLabel, draw_label, meal_label_fields
from souschef.meal.constants import (
    COMPONENT_GROUP_CHOICES,
    COMPONENT_GROUP_CHOICES_MAIN_DISH,
    COMPONENT_GROUP_CHOICES_SIDES,
)
from souschef.meal.models import (
    Component,
    Component_ingredient,
    Menu,
    Menu_component,
)
from souschef.member.models import (
    Client,
    DeliveryHistory,
    Route,
    get_ongoing_clients_at_date,
)
from souschef.order.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_ORDERED,
    SIZE_CHOICES_LARGE,
    SIZE_CHOICES_REGULAR,
)
from souschef.order.models import (
    DeliveryClient,
    KitchenItem,
    Order,
    component_group_sorting,
)

from . import tsp
from .filters import KitchenCountOrderFilter
from .forms import DishIngredientsForm

LOGO_IMAGE = os.path.join(
    settings.BASE_DIR,
    "160widthSR-Logo-Screen-PurpleGreen-HI-RGB1.jpg",
)
DELIVERY_STARTING_POINT_LAT_LONG = (45.516564, -73.575145)  # Santropol Roulant


def _get_pdf_file_path(filename, delivery_date) -> Path:
    delivery = delivery_date.strftime("%Y-%m-%d")
    today = datetime.now().replace(microsecond=0).isoformat()
    filepath = Path(filename)
    new_name = f"{filepath.name.rstrip('.pdf')}_{delivery}__{today}.pdf"
    return filepath.parent / delivery / new_name


def get_meals_label_file_path(delivery_date):
    return _get_pdf_file_path(settings.MEAL_LABELS_FILE, delivery_date)


def get_kitchen_count_file_path(delivery_date):
    return _get_pdf_file_path(settings.KITCHEN_COUNT_FILE, delivery_date)


def get_route_sheets_file_path(delivery_date):
    return _get_pdf_file_path(settings.ROUTE_SHEETS_FILE, delivery_date)


def get_orders_for_kitchen_count(order_statuses, delivery_date=None):
    return (
        Order.objects.get_orders(
            delivery_date=delivery_date, order_statuses=order_statuses
        )
        .order_by("client__route__pk", "pk")
        .prefetch_related("orders")
        .select_related("client__member", "client__route", "client__member__address")
        .only(
            "delivery_date",
            "status",
            "client__member__firstname",
            "client__member__lastname",
            "client__route__name",
            "client__member__address__latitude",
            "client__member__address__longitude",
        )
    )


def get_number_of_orders_in_status(orders, status):
    return len([o for o in orders if o.status == status])


def get_has_orders_in_status(orders, status):
    return get_number_of_orders_in_status(orders, status) > 0


def get_kitchen_count_context(delivery_date: date):
    orders = get_orders_for_kitchen_count(
        delivery_date=delivery_date,
        order_statuses=(ORDER_STATUS_ORDERED, ORDER_STATUS_CANCELLED),
    )

    return {
        "orders": orders,
        "has_ordered_orders": get_has_orders_in_status(orders, ORDER_STATUS_ORDERED),
        "has_cancelled_orders": get_has_orders_in_status(
            orders, ORDER_STATUS_CANCELLED
        ),
        "nb_of_ordered_orders": get_number_of_orders_in_status(
            orders, ORDER_STATUS_ORDERED
        ),
    }


class ReviewOrders(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    # Display all the order on a given day
    context_object_name = "orders"
    filterset_class = KitchenCountOrderFilter
    model = Order
    permission_required = "sous_chef.read"
    template_name = "review_orders.html"

    def get(self, request, *args, **kwargs):
        self._delivery_date = None
        if "delivery_date" in request.GET:
            self._delivery_date = date.fromisoformat(request.GET.get("delivery_date"))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return get_orders_for_kitchen_count(
            (ORDER_STATUS_ORDERED, ORDER_STATUS_CANCELLED), self._delivery_date
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders_refresh_date"] = None
        if LogEntry.objects.exists():
            log = LogEntry.objects.latest("action_time")
            context["orders_refresh_date"] = log

        # See also get_kitchen_count_context, used for the
        # "Generate orders" button.
        context["has_ordered_orders"] = get_has_orders_in_status(
            context["orders"], ORDER_STATUS_ORDERED
        )
        context["has_cancelled_orders"] = get_has_orders_in_status(
            context["orders"], ORDER_STATUS_CANCELLED
        )
        context["nb_of_ordered_orders"] = get_number_of_orders_in_status(
            context["orders"], ORDER_STATUS_ORDERED
        )
        context["delivery_date"] = self._delivery_date
        context["delivery_date_iso"] = (
            self._delivery_date and self._delivery_date.isoformat() or ""
        )
        return context


class MealInformation(LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    # Choose the main dish and its ingredients
    permission_required = "sous_chef.read"

    def get(self, request, **kwargs):
        """Display main dish and its ingredients."""

        if not request.GET.get("delivery_date"):
            raise Http404("delivery_date parameter missing")
        delivery_date = date.fromisoformat(request.GET["delivery_date"])

        #  get sides component
        try:
            sides_component = Component.objects.get(
                component_group=COMPONENT_GROUP_CHOICES_SIDES
            )
        except Component.DoesNotExist as e:
            raise Exception(
                "The database must contain exactly one component "
                + "having 'Component group' = 'Sides'."
            ) from e

        main_dishes = Component.objects.order_by(Lower("name")).filter(
            component_group=COMPONENT_GROUP_CHOICES_MAIN_DISH
        )

        if "id" in kwargs:
            # main dish has been chosen by user (onchange)
            main_dish = Component.objects.get(id=int(kwargs["id"]))
            # delete all existing ingredients for the date except for sides
            Component_ingredient.objects.filter(date=delivery_date).exclude(
                component=sides_component
            ).delete()
        else:
            # see if a menu exists for that date
            menu_comps = Menu_component.objects.filter(
                menu__date=delivery_date,
                component__component_group=COMPONENT_GROUP_CHOICES_MAIN_DISH,
            )
            if menu_comps:  # noqa: SIM108
                # main dish is known in the menu
                main_dish = menu_comps[0].component
            else:
                # take first main dish
                main_dish = main_dishes[0]

        recipe_ingredients = Component.get_recipe_ingredients(main_dish.id)
        # see if existing chosen ingredients for the main dish
        dish_ingredients = Component.get_day_ingredients(main_dish.id, delivery_date)
        # see if existing chosen ingredients for the sides
        sides_ingredients = Component.get_day_ingredients(
            sides_component.id, delivery_date
        )
        # need this for restore button
        recipe_changed = len(dish_ingredients) > 0 and set(dish_ingredients) != set(
            recipe_ingredients
        )
        # need this for update ingredients button
        ingredients_changed = len(dish_ingredients) == 0 or len(sides_ingredients) == 0

        if not dish_ingredients:
            # get recipe ingredients for the main dish
            dish_ingredients = recipe_ingredients
        form = DishIngredientsForm(
            initial={
                "maindish": main_dish.id,
                "ingredients": dish_ingredients,
                "sides_ingredients": sides_ingredients,
            }
        )
        # The form should be read-only if the user does not have the
        # permission to edit data.
        if not request.user.has_perm("sous_chef.edit"):
            [setattr(form.fields[k], "disabled", True) for k in form.fields]

        return render(
            request,
            "ingredients.html",
            {
                "form": form,
                "date": str(delivery_date),
                "delivery_date": delivery_date,
                "recipe_changed": recipe_changed,
                "ingredients_changed": ingredients_changed,
            },
        )

    def post(self, request):
        # Choose ingredients in main dish and in Sides

        # Prevent users to go further if they don't have the permission
        # to edit data.
        if not request.user.has_perm("sous_chef.edit"):
            raise PermissionDenied

        # print("Pick Ingredients POST request=", request.POST)  # For DEBUG
        delivery_date = date.fromisoformat(request.POST["delivery_date"])
        form = DishIngredientsForm(request.POST)
        # get sides component
        try:
            sides_component = Component.objects.get(
                component_group=COMPONENT_GROUP_CHOICES_SIDES
            )
        except Component.DoesNotExist as e:
            raise Exception(
                "The database must contain exactly one component "
                + "having 'Component group' = 'Sides' "
            ) from e

        if "_restore" in request.POST:
            # restore ingredients of main dish to those in recipe
            # delete all existing ingredients for the date except for sides
            Component_ingredient.objects.filter(date=delivery_date).exclude(
                component=sides_component
            ).delete()
            return HttpResponseRedirect(
                reverse_lazy("delivery:meal")
                + f"?delivery_date={request.POST['delivery_date']}"
            )
        elif "_update" in request.POST:
            # update ingredients of main dish and ingredients of sides
            if form.is_valid():
                ingredients = form.cleaned_data["ingredients"]
                sides_ingredients = form.cleaned_data["sides_ingredients"]
                component = form.cleaned_data["maindish"]
                # delete all main dish and sides ingredients for the date
                Component_ingredient.objects.filter(date=delivery_date).delete()
                # add revised ingredients for the date + dish
                for ing in ingredients:
                    ci = Component_ingredient(
                        component=component, ingredient=ing, date=delivery_date
                    )
                    ci.save()
                # add revised ingredients for the date + sides
                for ing in sides_ingredients:
                    ci = Component_ingredient(
                        component=sides_component, ingredient=ing, date=delivery_date
                    )
                    ci.save()
                # Create menu and its components
                compnames = [component.name]  # main dish
                # take first sorted name of each other component group
                for group, _ignore in COMPONENT_GROUP_CHOICES:
                    if group != COMPONENT_GROUP_CHOICES_MAIN_DISH:
                        compname = Component.objects.order_by(Lower("name")).filter(
                            component_group=group
                        )
                        if compname:
                            compnames.append(compname[0].name)
                Menu.create_menu_and_components(delivery_date, compnames)
                return HttpResponseRedirect(
                    reverse("delivery:meal")
                    + f"?delivery_date={request.POST['delivery_date']}"
                )
        # END IF
        return render(
            request,
            "ingredients.html",
            {
                "form": form,
                "date": str(delivery_date),
                "delivery_date": delivery_date,
                "recipe_changed": False,
                "ingredients_changed": True,
            },
        )


class RoutesInformation(LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    """Display route list page or download the route sheets report.

    Display all the route information for a given day.

    The view must first determine whether each of the routes with orders
    has been "organized by the user".

    By default the view displays a list of all the known routes
    indicating for each route the number of orders and its organize state.
    The view then creates the context to be rendered on the page.

    If the request includes argument "download=yes", the view obtains
    for each route the detailed orders to be delivered, sorts them in the
    chosen sequence and combines all the routes in a PDF report that
    is stored in the BASE_DIR and then downloaded by the browser.
    """

    permission_required = "sous_chef.read"

    @property
    def download(self):
        return self.request.GET.get("download", False)

    def get(self, request, *args, **kwargs):
        delivery_date = date.fromisoformat(request.GET["delivery_date"])
        routes = Route.objects.all()
        route_details = []
        all_configured = True
        for route in routes:
            clients = Order.objects.get_shippable_orders_by_route(
                route.id, delivery_date, exclude_non_geolocalized=True
            ).values_list("client__pk", flat=True)
            order_count = len(clients)
            try:
                delivery_history = DeliveryHistory.objects.get(
                    route=route, date=delivery_date
                )
                set1 = set(delivery_history.client_id_sequence)
                set2 = set(clients)
                has_organised = "yes" if set1 == set2 else "invalid"
            except DeliveryHistory.DoesNotExist:
                delivery_history = None
                has_organised = "no"
            except TypeError:
                # `client_id_sequence` is not iterable.
                has_organised = "invalid"

            route_details.append((route, order_count, has_organised, delivery_history))
            if order_count > 0 and has_organised != "yes":
                all_configured = False

        if not self.download:
            # display list of delivery routes on web page
            return render(
                request,
                "routes.html",
                {
                    "all_configured": all_configured,
                    "delivery_date": delivery_date,
                    "route_details": route_details,
                },
            )
        else:
            # download route sheets report as PDF
            if not all_configured:
                raise Http404
            routes_dict = {}
            for delivery_history in DeliveryHistory.objects.filter(date=delivery_date):
                route_list = Order.get_delivery_list(
                    delivery_date, delivery_history.route_id
                )
                route_list = sort_sequence_ids(
                    route_list, delivery_history.client_id_sequence
                )
                summary_lines, detail_lines = drs_make_lines(route_list)
                routes_dict[delivery_history.route_id] = {
                    "route": delivery_history.route,
                    "summary_lines": summary_lines,
                    "detail_lines": detail_lines,
                }
            # generate PDF report
            file_path = MultiRouteReport.routes_make_pages(routes_dict, delivery_date)
            response = download_pdf(file_path)
            # add serializable data in response header to be used in unit tests
            routes_dict_fortest = {}
            for key, item in routes_dict.items():
                routes_dict_fortest[key] = {
                    "route": item["route"].name,
                    "detail_lines": [
                        client.lastname for client in item["detail_lines"]
                    ],
                }
            response["routes_dict"] = json.dumps(routes_dict_fortest)
            return response


class CreateDelivery(LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = "sous_chef.edit"

    def post(self, request, pk, *args, **kwargs):
        delivery_date = date.fromisoformat(request.POST["delivery_date"])
        route = get_object_or_404(Route, pk=pk)
        if not Order.objects.get_shippable_orders_by_route(
            route.id, delivery_date, exclude_non_geolocalized=True
        ).exists():
            # No clients on this route.
            raise Http404

        try:
            DeliveryHistory.objects.get(route=route, date=delivery_date)
        except DeliveryHistory.DoesNotExist:
            DeliveryHistory.objects.create(
                route=route, date=delivery_date, vehicle=route.vehicle
            )
        return HttpResponseRedirect(
            reverse("delivery:edit_delivery_route", kwargs={"pk": pk})
            + f"?delivery_date={delivery_date.isoformat()}"
        )


class EditDeliveryRoute(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    model = DeliveryHistory
    fields = ("vehicle", "client_id_sequence", "comments")
    permission_required = "sous_chef.edit"
    template_name = "edit_delivery_route.html"

    def get(self, request, *args, **kwargs):
        self._delivery_date = date.fromisoformat(request.GET["delivery_date"])
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._delivery_date = date.fromisoformat(request.POST["delivery_date"])
        return super().post(request, *args, **kwargs)

    def get_object(self, *args, **kwargs):
        return get_object_or_404(
            DeliveryHistory.objects.select_related("route"),
            route=self.kwargs.get("pk"),
            date=self._delivery_date,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["delivery_history"] = self.object
        # This needs to be placed on the top when refactoring Route module.
        # It causes circular dependancy in current code structure.
        from souschef.member.views import get_clients_on_delivery_history  # noqa

        context["clients_on_delivery_history"] = get_clients_on_delivery_history(
            self.object,
            func_add_warning_message=lambda m: messages.add_message(
                self.request, messages.ERROR, m
            ),
        )
        context["delivery_date"] = self._delivery_date
        return context

    def get_success_url(self):
        return (
            reverse("delivery:routes")
            + f"?delivery_date={self._delivery_date.isoformat()}"
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Delivery on route %(route_name)s has been updated.")
            % {"route_name": self.object.route.name},
        )
        return response


# Route sheet report classes and functions.


def defineStyles(my_styles):
    """Define common styles for ReportLab objects.

    Adds reportlab.lib.styles.ParagraphStyle objects to my_styles.

    Args:
        my_styles: A reportlab.lib.styles.StyleSheet1 object.
    """
    my_styles.add(
        RLParagraphStyle(
            name="SmallRight",
            fontName="Helvetica",
            fontSize=7,
            alignment=rl_enums.TA_RIGHT,
        )
    )

    my_styles.add(
        RLParagraphStyle(
            name="NormalLeft",
            fontName="Helvetica",
            fontSize=10,
            alignment=rl_enums.TA_LEFT,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="NormalLeftBold",
            fontName="Helvetica-Bold",
            fontSize=10,
            alignment=rl_enums.TA_LEFT,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="NormalCenter",
            fontName="Helvetica",
            fontSize=10,
            alignment=rl_enums.TA_CENTER,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="NormalCenterBold",
            fontName="Helvetica-Bold",
            fontSize=10,
            alignment=rl_enums.TA_CENTER,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="NormalRight",
            fontName="Helvetica",
            fontSize=10,
            alignment=rl_enums.TA_RIGHT,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="NormalRightBold",
            fontName="Helvetica-Bold",
            fontSize=10,
            alignment=rl_enums.TA_RIGHT,
        )
    )

    my_styles.add(
        RLParagraphStyle(
            name="LargeLeft",
            fontName="Helvetica",
            fontSize=12,
            alignment=rl_enums.TA_LEFT,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="LargeCenter",
            fontName="Helvetica",
            fontSize=12,
            alignment=rl_enums.TA_CENTER,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="LargeRight",
            fontName="Helvetica",
            fontSize=12,
            alignment=rl_enums.TA_RIGHT,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="LargeBoldLeft",
            fontName="Helvetica-Bold",
            fontSize=12,
            alignment=rl_enums.TA_LEFT,
        )
    )
    my_styles.add(
        RLParagraphStyle(
            name="LargeBoldRight",
            fontName="Helvetica-Bold",
            fontSize=12,
            alignment=rl_enums.TA_RIGHT,
        )
    )

    my_styles.add(
        RLParagraphStyle(
            name="VeryLargeBoldLeft",
            fontName="Helvetica-Bold",
            fontSize=14,
            alignment=rl_enums.TA_LEFT,
            spaceAfter=5,
        )
    )

    my_styles.add(
        RLParagraphStyle(
            name="HugeBoldCenter",
            fontName="Helvetica-Bold",
            fontSize=20,
            alignment=rl_enums.TA_CENTER,
        )
    )


class MultiRouteReport:
    """Namespace for Route sheet report data structures and logic.

    This class is never instantiated.

    Uses ReportLab see http://www.reportlab.com/documentation/faq/
    """

    # (class attribute) last page number on which a ReportLab Table has split
    table_split = None

    # (class attribute) report document instance
    document = None

    # (class attribute) page number on which route starts
    route_start_page = None

    class RLMultiRouteTable(RLTable):
        """Custom table for route sheets that is monitored for table splits."""

        def onSplit(self, table, **kwargs):
            """Override method to detect table splits.

            ReportLab calls this twice for each split :
              first call has the table with rows that fit on current page,
              second call has the table with the rest of the rows.
            """
            MultiRouteReport.table_split = MultiRouteReport.document.page
            # @lamontfr 20170522 : Please do not remove, used for DEBUGGING
            # print("onSplit **********************",
            #       "page=", MultiRouteReport.document.page,
            #       "FIRST CLIENT _cellvalues[1][0][0].text=",
            #       repr(table._cellvalues[1][0][0].text),
            #       "LAST CLIENT _cellvalues[-1][0][0].text=",
            #       repr(table._cellvalues[-1][0][0].text),
            # )
            super().onSplit(table, **kwargs)

    class RLMultiRouteDocTemplate(RLSimpleDocTemplate):
        """Custom document template for route sheets having multiple tables."""

        def __init__(self, *args, **kwargs):
            """Init class and ensure that we have a page footer function.

            Args:
                *args
                    (required)
                        route_sheets_file : string, a file name.
                **kwargs
                    (required)
                        footerFunc : callable, draws the footer.
                    (optional, see also reportlab SimpleDocTemplate)
                        leftMargin : integer, inches.
                        rightMargin : integer, inches.
                        bottomMargin : integer, inches.
            """
            try:
                self.footerFunc = kwargs.pop("footerFunc")
            except KeyError as e:
                raise KeyError(
                    self.__class__.__name__ + " missing kwarg : footerFunc"
                ) from e
            super().__init__(*args, **kwargs)

        def afterPage(self, *args, **kwargs):
            """Override method for footer and blanks based on table splits.

            If table has split on this page, insert footer that tells reader
            to look for continuation on back side or on next sheet.
            If table finishes on the front side of a page, insert a blank
            page after it if necessary to ensure that two sided printing will
            show the next table on the front side of the next sheet.
            """
            if MultiRouteReport.table_split == self.page:
                # table has split, therefore route continues on next page
                if (self.page - MultiRouteReport.route_start_page + 1) % 2 != 0:
                    # split occured at bottom of front side of sheet (odd page)
                    self.footerFunc(
                        self, "** SUITE AU VERSO / CONTINUED ON REVERSE SIDE **"
                    )
                else:
                    # split occured at bottom of back side of sheet (even page)
                    self.footerFunc(
                        self, "** VOIR FEUILLE SUIVANTE / SEE NEXT SHEET **"
                    )
            else:
                # no table split means route finishes on this page
                if (self.page - MultiRouteReport.route_start_page + 1) % 2 != 0:
                    # route finishes on odd page, add a blank page
                    self.canv.showPage()
                # the next route, if any, will start on next document page
                MultiRouteReport.route_start_page = self.page + 1

    # static method
    def routes_make_pages(routes_dict, delivery_date):
        """Generate the route sheets pages as a PDF file.

        Ensures that a new route starts on the front side of a sheet,
        by adding a blank page if necessary.
        The page footer indicates whether the delivery route continues
        on the reverse side of the sheet or on the next sheet.

        Args:
            routes_dict : A dictionary {<route id>:<value>, ...} where
              <value> is a dictionary containing 3 items :
                'route' : a Route object.
                'summary_lines' : A list of RouteSummaryLine objects, sorted by
                                  component_group name (main dish first).
                'detail_lines' : A list of DeliveryClient objects
                                 (see order/models.py),
                                 sorted according to delivery history sequence.

        Returns:
            An integer : The number of pages generated.
        """
        PAGE_HEIGHT = 11.0 * rl_inch
        PAGE_WIDTH = 8.5 * rl_inch

        styles = rl_getSampleStyleSheet()
        defineStyles(styles)

        def drawHeader(canvas, doc):
            """Draw the header and footer.

            Args:
                canvas : A reportlab.pdfgen.canvas.Canvas object.
                doc : A reportlab.platypus.SimpleDocTemplate object.
            """
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 12)
            canvas.drawString(
                x=1.5 * rl_inch,
                y=PAGE_HEIGHT + 0.30 * rl_inch,
                text="Santropol Roulant",
            )
            canvas.setFont("Helvetica", 12)
            canvas.drawString(
                x=1.5 * rl_inch,
                y=PAGE_HEIGHT + 0.15 * rl_inch,
                text="Tel. : (514) 284-9335",
            )
            canvas.setFont("Helvetica", 10)
            canvas.drawString(
                x=1.5 * rl_inch,
                y=PAGE_HEIGHT - 0.0 * rl_inch,
                text="{}".format(delivery_date.strftime("%a., %d %B %Y")),
            )
            canvas.drawString(
                x=3.25 * rl_inch,
                y=PAGE_HEIGHT + 0.30 * rl_inch,
                text="(Ce document contient des informations CONFIDENTIELLES.)",
            )
            canvas.drawString(
                x=3.25 * rl_inch,
                y=PAGE_HEIGHT + 0.15 * rl_inch,
                text="(This document contains CONFIDENTIAL information.)",
            )
            canvas.drawRightString(
                x=PAGE_WIDTH - 0.75 * rl_inch,
                y=PAGE_HEIGHT + 0.30 * rl_inch,
                text=f"Page {doc.page - MultiRouteReport.route_start_page + 1:d}",
            )
            canvas.drawInlineImage(
                LOGO_IMAGE,
                0.5 * rl_inch,
                PAGE_HEIGHT - 0.2 * rl_inch,
                width=0.8 * rl_inch,
                height=0.7 * rl_inch,
            )
            canvas.restoreState()

        def drawFooter(doc, text):
            """Draw the page footer.

            Args:
                doc : A reportlab.platypus.SimpleDocTemplate object.
                text : A string to place in the footer.
            """
            doc.canv.saveState()
            doc.canv.setFont("Helvetica", 14)
            doc.canv.drawCentredString(
                x=4.0 * rl_inch, y=PAGE_HEIGHT - 10.5 * rl_inch, text=text
            )
            doc.canv.restoreState()

        def go():
            """Generate the pages.

            Returns:
                An integer : The number of pages generated.
            """
            file_path = get_route_sheets_file_path(delivery_date)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            doc = MultiRouteReport.RLMultiRouteDocTemplate(
                str(file_path),
                leftMargin=0.5 * rl_inch,
                rightMargin=0.5 * rl_inch,
                bottomMargin=0.5 * rl_inch,
                footerFunc=drawFooter,
            )
            # initialize
            MultiRouteReport.table_split = 0
            MultiRouteReport.document = doc
            MultiRouteReport.route_start_page = 1
            story = []
            first_route = True

            # TODO Loop over routes
            for route in routes_dict.values():
                if not route["summary_lines"]:
                    # empty route : skip it
                    continue
                # begin Summary section
                if not first_route:
                    # next route must start on a new page
                    story.append(RLPageBreak())
                rows = []
                rows.append(
                    [
                        RLParagraph("PLAT / DISH", styles["NormalLeftBold"]),
                        RLParagraph("Qté / Qty", styles["NormalCenterBold"]),
                    ]
                )
                for sl in route["summary_lines"]:
                    rows.append(
                        [
                            RLParagraph(sl.component_group_trans, styles["NormalLeft"]),
                            RLParagraph(str(sl.rqty + sl.lqty), styles["NormalCenter"]),
                        ]
                    )
                tab = MultiRouteReport.RLMultiRouteTable(
                    rows,
                    colWidths=(100, 60),
                    style=[
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 1, rl_colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ],
                    hAlign="LEFT",
                )
                story.append(tab)
                # end Summary section

                # Route name
                story.append(RLSpacer(1, 0.25 * rl_inch))
                story.append(RLParagraph(route["route"].name, styles["HugeBoldCenter"]))
                story.append(RLSpacer(1, 0.25 * rl_inch))
                story.append(
                    RLParagraph(
                        "- DÉBUT DE LA ROUTE / START ROUTE -", styles["LargeLeft"]
                    )
                )
                story.append(RLSpacer(1, 0.125 * rl_inch))

                # begin Detail section
                rows = []
                line = 0
                tab_style = RLTableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])
                rows.append(
                    [
                        RLParagraph("Client", styles["NormalLeft"]),
                        RLParagraph("Note", styles["NormalLeft"]),
                        RLParagraph("Items", styles["NormalLeft"]),
                        RLParagraph("", styles["NormalLeft"]),
                    ]
                )
                tab_style.add("LINEABOVE", (0, 0), (-1, 0), 1, rl_colors.black)
                line += 1
                for c in route["detail_lines"]:
                    tab_style.add(
                        "LINEABOVE", (0, line), (-1, line), 1, rl_colors.black
                    )
                    rows.append(
                        [
                            # client
                            [
                                RLParagraph(
                                    c.firstname + " " + c.lastname,
                                    styles["VeryLargeBoldLeft"],
                                ),
                                RLParagraph(c.street, styles["LargeLeft"]),
                                RLParagraph("Apt " + c.apartment, styles["LargeLeft"])
                                if c.apartment
                                else [],
                                RLParagraph(c.phone, styles["LargeLeft"]),
                            ],
                            # note
                            RLParagraph(c.delivery_note, styles["LargeLeft"]),
                            # items
                            (
                                [
                                    RLParagraph(
                                        i.component_group_trans, styles["LargeLeft"]
                                    )
                                    for i in c.delivery_items
                                ]
                                + [
                                    RLParagraph("Facture / Bill", styles["LargeLeft"])
                                    if c.include_a_bill
                                    else []
                                ]
                            ),
                            # quantity
                            [
                                RLParagraph(str(i.total_quantity), styles["LargeRight"])
                                for i in c.delivery_items
                            ],
                        ]
                    )
                    line += 1
                # END for
                # add row for number of clients
                rows.append(
                    [
                        [
                            RLParagraph("- FIN DE LA ROUTE -", styles["LargeLeft"]),
                            RLParagraph("- END OF ROUTE- ", styles["LargeLeft"]),
                        ],
                        [
                            RLParagraph("Nombre d'arrêts :", styles["LargeRight"]),
                            RLParagraph("Number of Stops :", styles["LargeRight"]),
                        ],
                        RLParagraph(str(line - 1), styles["LargeLeft"]),
                        RLParagraph("", styles["LargeLeft"]),
                    ]
                )
                #
                tab_style.add(
                    "LINEBELOW", (0, line - 1), (-1, line - 1), 1, rl_colors.black
                )
                tab = MultiRouteReport.RLMultiRouteTable(
                    rows, colWidths=(140, 255, 100, 20), repeatRows=1
                )
                tab.setStyle(tab_style)
                story.append(tab)
                # end Detail section
                first_route = False
            # END for

            # build full document
            doc.build(
                story,
                onFirstPage=drawHeader,
                onLaterPages=drawHeader,
            )

            return file_path

        # END def
        return go()  # returns the file path


# END Route sheet report.


# Kitchen count report view, helper classes and functions


class IngredientsMissingError(Exception):
    pass


def get_kitchen_list(delivery_date: date) -> Dict[int, KitchenItem]:
    # Display kitchen count report for given delivery date
    # and generate meal labels.
    #  get sides component
    try:
        sides_component = Component.objects.get(
            component_group=COMPONENT_GROUP_CHOICES_SIDES
        )
    except Component.DoesNotExist as e:
        raise Exception(
            "The database must contain exactly one component "
            + "having 'Component group' = 'Sides' "
        ) from e
    # check if main dish ingredients were confirmed
    main_ingredients = Component_ingredient.objects.filter(date=delivery_date).exclude(
        component=sides_component
    )
    # check if sides ingredients were confirmed
    sides_ingredients = Component_ingredient.objects.filter(
        component=sides_component, date=delivery_date
    )
    if len(main_ingredients) == 0 or len(sides_ingredients) == 0:
        raise IngredientsMissingError

    kitchen_list_unfiltered = Order.get_kitchen_items(delivery_date)

    # filter out route=None clients and not geolocalized clients
    kitchen_list: Dict[int, KitchenItem] = {}
    geolocalized_client_ids = list(
        Client.objects.filter(
            pk__in=kitchen_list_unfiltered.keys(),
            member__address__latitude__isnull=False,
            member__address__longitude__isnull=False,
        ).values_list("pk", flat=True)
    )

    for client_id, kitchen_item in kitchen_list_unfiltered.items():
        if kitchen_item.routename is not None and client_id in geolocalized_client_ids:
            kitchen_list[client_id] = kitchen_item

    return kitchen_list


def make_kitchen_count(
    kitchen_list: Dict[int, KitchenItem],
    component_lines: List[ComponentLine],
    meal_lines: List[MealLine],
    delivery_date: date,
) -> Path | None:
    if not component_lines:
        # we have no orders on that date
        return
    preperation_lines_with_incompatible_ingr = kcr_make_preparation_lines(
        kitchen_list, "only_clients_with_incompatible_ingredients"
    )
    preperation_lines_without_incompatible_ingr = kcr_make_preparation_lines(
        kitchen_list, "only_clients_without_incompatible_ingredients"
    )
    return kcr_make_pages(  # kitchen count as PDF
        delivery_date,
        component_lines,
        meal_lines,  # summary
        preperation_lines_with_incompatible_ingr,
        preperation_lines_without_incompatible_ingr,
    )  # detail


def make_labels(
    kitchen_list: Dict[int, KitchenItem],
    component_lines: List[ComponentLine],
    delivery_date: date,
) -> Path | None:
    if not component_lines:
        return
    return kcr_make_labels(  # meal labels as PDF
        delivery_date,
        kitchen_list,
        # main dish name
        component_lines[0].name,
        # main dish ingredients
        component_lines[0].ingredients,
        # sides ingredients
        component_lines[1].ingredients,
    )


def download_pdf(file_path: Path):
    with open(file_path, "rb") as f:
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
        response.write(f.read())
        return response


class KitchenCount(LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = "sous_chef.read"

    def get(self, request, *args, **kwargs):
        delivery_date = date.fromisoformat(request.GET["delivery_date"])
        download = request.GET.get("download")

        try:
            kitchen_list = get_kitchen_list(delivery_date)
        except IngredientsMissingError:
            # some ingredients not confirmed, must go back one step
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "Please check main dish and confirm "
                    "all ingredients before proceeding to kitchen count."
                ),
            )
            return HttpResponseRedirect(
                reverse_lazy("delivery:meal")
                + f"?delivery_date={request.GET['delivery_date']}"
            )

        component_lines = kcr_make_component_lines(kitchen_list, delivery_date)
        meal_lines = kcr_make_meal_lines(kitchen_list)

        file_path = None
        if download == "kitchen_count":
            file_path = make_kitchen_count(
                kitchen_list, component_lines, meal_lines, delivery_date
            )
        elif download == "labels":
            file_path = make_labels(kitchen_list, component_lines, delivery_date)

        if file_path:
            return download_pdf(file_path)

        return render(
            request,
            "kitchen_count.html",
            {
                "component_lines": component_lines,
                "delivery_date": delivery_date,
                "has_data": bool(kitchen_list),
                "meal_lines": meal_lines,
            },
        )


@dataclass
class ComponentLine:
    # ex. main dish, dessert etc
    component_group: str
    # component name
    name: str
    # ingredients in main dish
    ingredients: str
    # Quantity of regular size main dishes
    rqty: int = 0
    # Quantity of large size main dishes
    lqty: int = 0


# Special Meal Line on Kitchen Count.
# structure: first line = field name, second line = default value
meal_line_fields = [
    # str: Lastname and abbreviated first name
    "client",
    "",
    # str: Quantity of regular size main dishes
    "rqty",
    "",
    # str: Quantity of large size main dishes
    "lqty",
    "",
    # str: Ingredients that clashes
    "ingr_clash",
    "",
    # str: Other ingredients to avoid
    "rest_ingr",
    "",
    # str: Restricted items
    "rest_item",
    "",
    "span",
    "1",
    # str: food preparation
    "food_prep",
    "",
]  # Number of lines to "rowspan" in table
MealLine = collections.namedtuple("MealLine", meal_line_fields[0::2])


def meal_line(kititm):
    """Builds a line for the main section of the Kitchen Count Report.

    Given a client's special requirements, assemble the fields of a line
    that will be displayed / printed in the Kitchen Count Report.

    Args:
        kititm : A KitchenItem object (see order/models)

    Returns:
        A MealLine object
    """
    return MealLine(
        client=format_client_name(kititm.firstname, kititm.lastname),
        rqty=(kititm.meal_qty if kititm.meal_size == SIZE_CHOICES_REGULAR else 0),
        lqty=(kititm.meal_qty if kititm.meal_size == SIZE_CHOICES_LARGE else 0),
        ingr_clash="",
        rest_ingr=", ".join(
            sorted(
                list(
                    set(kititm.avoid_ingredients) - set(kititm.incompatible_ingredients)
                )
            )
        ),
        rest_item=", ".join(kititm.restricted_items),
        span="1",
        food_prep=", ".join(sorted(kititm.preparation)),
    )


def kcr_make_meal_lines(kitchen_list: Dict[int, KitchenItem]) -> List[MealLine]:
    meal_lines: List[MealLine] = []
    specials_regular_total_qty = 0
    specials_large_total_qty = 0
    side_clashes_regular_total_qty = 0
    side_clashes_large_total_qty = 0
    # Ingredients clashes (and other columns)
    regular_subtotal = 0
    large_subtotal = 0
    clients = iter(
        sorted(
            [
                (client_id, kitchen_item)
                for client_id, kitchen_item in kitchen_list.items()
                if kitchen_item.incompatible_ingredients
            ],
            key=lambda item: item[1].incompatible_ingredients,
        )
    )

    # first line of a combination of ingredients
    line_start = 0
    regular_subtotal = 0
    large_subtotal = 0
    client_id, kitchen_item = next(clients, (0, 0))  # has end sentinel
    while client_id > 0:
        if regular_subtotal == 0 and large_subtotal == 0:
            # add line for subtotal at top of combination
            meal_lines.append(MealLine(*meal_line_fields[1::2]))
        ingredients_clashing = kitchen_item.incompatible_ingredients
        meal_lines.append(meal_line(kitchen_item))

        if kitchen_item.meal_size == SIZE_CHOICES_REGULAR:
            regular_subtotal += kitchen_item.meal_qty
        else:
            large_subtotal += kitchen_item.meal_qty

        if kitchen_item.sides_clashes:
            if kitchen_item.meal_size == SIZE_CHOICES_REGULAR:
                side_clashes_regular_total_qty += kitchen_item.meal_qty
            else:
                side_clashes_large_total_qty += kitchen_item.meal_qty

        client_id, kitchen_item = next(clients, (0, 0))
        if (
            client_id == 0
            or ingredients_clashing != kitchen_item.incompatible_ingredients
        ):
            # last line of this combination of clashing ingredients
            line_end = len(meal_lines)
            # set rowspan to total number of lines for this combination of clashing
            # ingredients
            meal_lines[line_start] = meal_lines[line_start]._replace(
                client="SUBTOTAL",
                rqty=regular_subtotal,
                lqty=large_subtotal,
                ingr_clash=", ".join(ingredients_clashing),
                span=str(line_end - line_start),
            )
            specials_regular_total_qty, specials_large_total_qty = (
                specials_regular_total_qty + regular_subtotal,
                specials_large_total_qty + large_subtotal,
            )
            regular_subtotal, large_subtotal = (0, 0)
            # hide ingredients for lines following the first
            for j in range(line_start + 1, line_end):
                meal_lines[j] = meal_lines[j]._replace(span="-1")
            # Add a blank line as separator
            meal_lines.append(MealLine(*meal_line_fields[1::2]))
            # first line of next combination of ingredients
            line_start = len(meal_lines)
    # END WHILE

    meal_lines.append(
        MealLine(*meal_line_fields[1::2])._replace(
            rqty=specials_regular_total_qty,
            lqty=specials_large_total_qty,
            ingr_clash="TOTAL SPECIALS",
        )
    )
    meal_lines.append(
        MealLine(*meal_line_fields[1::2])._replace(
            rqty=side_clashes_regular_total_qty,
            lqty=side_clashes_large_total_qty,
            ingr_clash="TOTAL SIDE CLASHES",
        )
    )

    return meal_lines


def kcr_make_component_lines(
    kitchen_list: Dict[int, KitchenItem], kcr_date
) -> List[ComponentLine]:
    """Generate the sections and lines for the kitchen count report.

    Count all the dishes that have to be prepared and identify all the
    special client requirements such as disliked ingredients and
    restrictions.

    Args:
        kitchen_list : A dictionary of KitchenItem objects (see
            order/models) which contain detailed information about
            all the meals that have to be prepared for the day and
            the client requirements and restrictions.
        kcr_date : A date.datetime object giving the date on which the
            meals will be delivered.

    Returns:
        Component (dishes) summary lines.
    """
    # Build component summary
    component_lines: Dict[str, ComponentLine] = {}
    for _k, item in kitchen_list.items():
        for component_group, meal_component in item.meal_components.items():
            component_lines.setdefault(
                component_group,
                ComponentLine(
                    # find the translated name of the component group
                    component_group=next(
                        cg for cg in COMPONENT_GROUP_CHOICES if cg[0] == component_group
                    )[1],
                    name="",
                    ingredients="",
                ),
            )
            if (
                component_group == COMPONENT_GROUP_CHOICES_MAIN_DISH
                and component_lines[component_group].name == ""
            ):
                # For the main dish we need to get the ingredients.
                component_lines[component_group].name = meal_component.name
                component_lines[component_group].ingredients = ", ".join(
                    [
                        ing.name
                        for ing in Component.get_day_ingredients(
                            meal_component.id, kcr_date
                        )
                    ]
                )
            if (
                component_group == COMPONENT_GROUP_CHOICES_MAIN_DISH
                and item.meal_size == SIZE_CHOICES_LARGE
            ):
                component_lines[component_group].lqty = (
                    component_lines[component_group].lqty + meal_component.qty
                )
            else:
                component_lines[component_group].rqty = (
                    component_lines[component_group].rqty + meal_component.qty
                )
        # END FOR
    # END FOR
    # Sort component summary
    items = component_lines.items()
    if items:
        component_lines_sorted = [component_lines[COMPONENT_GROUP_CHOICES_MAIN_DISH]]
        component_lines_sorted.extend(
            sorted(
                [v for k, v in items if k != COMPONENT_GROUP_CHOICES_MAIN_DISH],
                key=lambda x: x.component_group,
            )
        )
    else:
        return []

    # Add sides as the second line
    sides_component = Component.objects.get(
        component_group=COMPONENT_GROUP_CHOICES_SIDES
    )
    sides_line = ComponentLine(
        component_group=sides_component.name,
        name=sides_component.name,
        ingredients=", ".join(
            [
                ing.name
                for ing in Component.get_day_ingredients(sides_component.id, kcr_date)
            ]
        ),
    )
    component_lines_sorted.insert(1, sides_line)

    return component_lines_sorted


def format_client_name(firstname, lastname):
    return f"{lastname}, {firstname[:2]}."


@dataclass
class PreparationLine:
    preparation_method: str
    quantity: int
    client_names: List[str]


def get_portions(regular_qty, large_qty):
    # A large portion is worth 1.5 regular portions.
    portions = regular_qty + large_qty * 1.5
    # Remove '.0' (keep number as integer if there is no decimal part)
    if portions == int(portions):
        portions = int(portions)
    return portions


def qty_paragraph(qty: int | float, style):
    # 0 will not be displayed
    return RLParagraph(str(qty or ""), style)


def kcr_make_preparation_lines(
    kitchen_list: Dict[int, KitchenItem], client_filter
) -> List[PreparationLine]:
    """Get food preparation method for clients not having clashing (incompatible)
    ingredients."""
    if client_filter == "only_clients_with_incompatible_ingredients":

        def select_item(item):
            return bool(item.incompatible_ingredients)
    elif client_filter == "only_clients_without_incompatible_ingredients":

        def select_item(item):
            return not item.incompatible_ingredients
    else:
        raise ValueError(f"Incompatible client_filter: {client_filter}")

    items = [item for item in kitchen_list.values() if select_item(item)]

    # Group KitchenItem per preparation method
    items_per_preparation = collections.defaultdict(list)
    for item in items:
        for prep in item.preparation:
            items_per_preparation[prep].append(item)

    preparation_lines = []
    for prep in sorted(items_per_preparation.keys()):
        client_names = sorted(
            format_client_name(item.firstname, item.lastname)
            + (f" (x {item.meal_qty})" if item.meal_qty > 1 else "")
            for item in items_per_preparation[prep]
        )
        quantity = sum(item.meal_qty for item in items_per_preparation[prep])

        preparation_lines.append(
            PreparationLine(
                preparation_method=prep,
                quantity=quantity,
                client_names=client_names,
            )
        )

    return preparation_lines


def kcr_make_pages(
    kcr_date,
    component_lines: List[ComponentLine],
    meal_lines: List[MealLine],
    preperation_lines_with_incompatible_ingr: List[PreparationLine],
    preperation_lines_without_incompatible_ingr: List[PreparationLine],
):
    """Generate the kitchen count report pages as a PDF file.

    Uses ReportLab see http://www.reportlab.com/documentation/faq/

    Args:
        kcr_date: The delivery date of the meals.
        component_lines: A list of ComponentLine objects, the summary of
            component quantities and sizes for the date's meal.
        meal_lines: A list of MealLine objects, the details of the clients
            for the date that have ingredients clashing with those in main dish.
        preperation_lines_with_incompatible_ingr: List[PreperationLine]
        preperation_lines_without_incompatible_ingr: List[PreperationLine]

    Returns:
        An integer : The number of pages generated.
    """
    PAGE_HEIGHT = 14.0 * rl_inch
    PAGE_WIDTH = 8.5 * rl_inch

    styles = rl_getSampleStyleSheet()
    defineStyles(styles)

    def drawHeader(canvas, doc):
        """Draw the header part common to all pages.

        Args:
            canvas : A reportlab.pdfgen.canvas.Canvas object.
            doc : A reportlab.platypus.SimpleDocTemplate object.
        """
        canvas.setFont("Helvetica", 14)
        y = PAGE_HEIGHT - 0.3 * rl_inch
        canvas.drawString(x=1.9 * rl_inch, y=y, text="Kitchen count report")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(
            x=6.0 * rl_inch,
            y=y,
            text="{}".format(kcr_date.strftime("%a., %d %B %Y")),
        )
        canvas.drawRightString(
            x=PAGE_WIDTH - 0.75 * rl_inch,
            y=y,
            text=f"Page {doc.page:d}",
        )

    def myFirstPage(canvas: Canvas, doc):
        """Draw the complete header for the first page.

        Args:
            canvas : A reportlab.pdfgen.canvas.Canvas object.
            doc : A reportlab.platypus.SimpleDocTemplate object.
        """
        canvas.saveState()
        drawHeader(canvas, doc)
        canvas.drawInlineImage(
            LOGO_IMAGE,
            0.75 * rl_inch,
            PAGE_HEIGHT - 1.0 * rl_inch,
            width=1.0 * rl_inch,
            height=0.85 * rl_inch,
        )
        canvas.restoreState()

    def myLaterPages(canvas: Canvas, doc):
        """Draw the complete header for all pages except the first one.

        Args:
            canvas : A reportlab.pdfgen.canvas.Canvas object.
            doc : A reportlab.platypus.SimpleDocTemplate object.
        """
        canvas.saveState()
        drawHeader(canvas, doc)
        canvas.restoreState()

    def get_component_table():
        small_left = deepcopy(styles["SmallRight"])
        small_left.alignment = 0

        rows = []
        rows.append(
            [
                RLParagraph("Component", styles["NormalLeft"]),
                RLParagraph("Total", styles["NormalLeft"]),
                "",
                "",
                RLParagraph("Ingredients", styles["NormalLeft"]),
            ]
        )
        rows.append(
            [
                "",
                RLParagraph("Regular", styles["SmallRight"]),
                RLParagraph("Large", styles["SmallRight"]),
                RLParagraph("Portions", styles["SmallRight"]),
                "",
            ]
        )
        for cl in component_lines:
            portions = get_portions(cl.rqty, cl.lqty)
            rows.append(
                [
                    cl.component_group,
                    qty_paragraph(cl.rqty, styles["NormalRight"]),
                    qty_paragraph(cl.lqty, styles["NormalRight"]),
                    # To make reading the table easier, do not display the portions if
                    # there are no large quantity, as then the number of portions would
                    # be the same as the regular quantity.
                    qty_paragraph(portions, styles["NormalRight"]) if cl.lqty else "",
                    RLParagraph(cl.ingredients, styles["NormalLeft"]),
                ]
            )
        return RLTable(
            rows,
            colWidths=(100, 40, 40, 40, 300),
            style=[
                # style, start cell, end cell, params
                ("VALIGN", (0, 2), (-1, -1), "TOP"),
                ("LINEABOVE", (0, 0), (-1, 0), 1, rl_colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 1, rl_colors.black),
                ("LINEBEFORE", (0, 0), (0, 0), 1, rl_colors.black),
                ("LINEAFTER", (-1, 0), (-1, 0), 1, rl_colors.black),
                ("SPAN", (1, 0), (2, 0)),
            ],
        )

    def get_food_preperation_table(preperation_lines, heading_suffix):
        rows = []
        line = 0
        tab_style = RLTableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])
        rows.append(
            [
                RLParagraph("Food Preparation", styles["NormalLeft"]),
                RLParagraph("Quantity", styles["NormalRight"]),
                "",
                [
                    RLParagraph("Clients", styles["NormalLeft"]),
                    RLParagraph(f"({heading_suffix})", styles["NormalLeftBold"]),
                ],
            ]
        )
        tab_style.add("LINEABOVE", (0, line), (-1, line), 1, rl_colors.black)
        tab_style.add("LINEBELOW", (0, line), (-1, line), 1, rl_colors.black)
        tab_style.add("LINEBEFORE", (0, line), (0, line), 1, rl_colors.black)
        tab_style.add("LINEAFTER", (-1, line), (-1, line), 1, rl_colors.black)
        line += 1

        for prepline in preperation_lines:
            rows.append(
                [
                    RLParagraph(prepline.preparation_method, styles["LargeBoldLeft"]),
                    RLParagraph(str(prepline.quantity), styles["NormalRightBold"]),
                    "",
                    RLParagraph(
                        ";&nbsp;&nbsp; ".join(prepline.client_names),
                        styles["NormalLeft"],
                    ),
                ]
            )
        tab = RLTable(rows, colWidths=(150, 50, 10, 310), repeatRows=1)
        tab.setStyle(tab_style)
        return tab

    def go():
        """Generate the pages.

        Returns:
            An integer : The number of pages generated.
        """
        file_path = get_kitchen_count_file_path(kcr_date)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        doc = RLSimpleDocTemplate(str(file_path), pagesize=pagesizes.legal)
        story = []

        # begin Summary section

        # Menu name
        menu = component_lines[0].name if component_lines else ""
        title_style = deepcopy(styles["NormalLeftBold"])
        title_style.spaceBefore = 0
        title_style.leftIndent = 60
        title_style.fontSize = 14
        story.append(RLParagraph(menu, title_style))
        story.append(RLSpacer(1, 0.5 * rl_inch))

        tab = get_component_table()
        story.append(tab)
        story.append(RLSpacer(1, 0.25 * rl_inch))
        # end Summary section

        # begin Detail section
        rows = []
        line = 0
        tab_style = RLTableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])
        rows.append(
            [
                RLParagraph("Clashing ingredients", styles["NormalLeft"]),
                RLParagraph("Reg", styles["NormalRight"]),
                RLParagraph("Lrg", styles["NormalRight"]),
                RLParagraph("Portions", styles["NormalRight"]),
                "",
                RLParagraph("Client & Food Prep", styles["NormalLeft"]),
                RLParagraph("Other restrictions", styles["NormalLeft"]),
            ]
        )
        tab_style.add("LINEABOVE", (0, line), (-1, line), 1, rl_colors.black)
        tab_style.add("LINEBEFORE", (0, line), (0, line), 1, rl_colors.black)
        tab_style.add("LINEAFTER", (-1, line), (-1, line), 1, rl_colors.black)
        line += 1
        for ml in meal_lines:
            if ml.ingr_clash and not ml.client:
                # Total line at the bottom
                rows.append(
                    [
                        RLParagraph(ml.ingr_clash or "∅", styles["NormalLeftBold"]),
                        qty_paragraph(ml.rqty, styles["NormalRightBold"]),
                        qty_paragraph(ml.lqty, styles["NormalRightBold"]),
                        qty_paragraph(
                            get_portions(ml.rqty, ml.lqty), styles["NormalRightBold"]
                        ),
                        "",
                        "",
                    ]
                )
                tab_style.add("LINEABOVE", (0, line), (-1, line), 1, rl_colors.black)
            elif ml.ingr_clash or ml.client:
                # not a blank separator line
                if ml.span != "-1":
                    # line has ingredient clash data
                    tab_style.add("SPAN", (0, line), (0, line + int(ml.span) - 1))
                    tab_style.add(
                        "LINEABOVE", (0, line), (-1, line), 1, rl_colors.black
                    )
                    # for dashes, must use LINEABOVE because dashes do not work
                    #   with LINEBELOW; seems to be a bug in ReportLab see :
                    #   reportlab/platypus/tables.py line # 1309
                    tab_style.add(
                        "LINEABOVE",  # op
                        (1, line + 1),  # start
                        (-1, line + 1),  # stop
                        1,  # weight
                        rl_colors.black,  # color
                        None,  # cap
                        [1, 2],
                    )  # dashes
                    value = RLParagraph(ml.ingr_clash or "∅", styles["LargeBoldLeft"])
                else:
                    # span = -1 means clash data must be blanked out
                    #   because it is the same as the initial spanned row
                    value = ""
                # END IF
                if ml.client == "SUBTOTAL":
                    client = ""
                    qty_style = "LargeBoldRight"
                else:
                    client = ml.client
                    qty_style = "NormalRight"
                food_prep = f"({ml.food_prep})" if ml.food_prep else ""
                rows.append(
                    [
                        value,
                        RLParagraph(str(ml.rqty or ""), styles[qty_style]),
                        RLParagraph(str(ml.lqty or ""), styles[qty_style]),
                        RLParagraph(
                            str(get_portions(ml.rqty, ml.lqty) or ""),
                            styles[qty_style],
                        ),
                        "",
                        [
                            RLParagraph(client, styles["NormalLeft"]),
                            RLParagraph(food_prep, styles["NormalLeftBold"]),
                        ],
                        [
                            RLParagraph(
                                ml.rest_ingr
                                + (" ;" if ml.rest_ingr and ml.rest_item else ""),
                                styles["NormalLeft"],
                            ),
                            RLParagraph(ml.rest_item, styles["NormalLeftBold"]),
                        ],
                    ]
                )
                # END IF
                line += 1
            # END IF
        # END FOR
        tab = RLTable(rows, colWidths=(130, 35, 35, 50, 20, 100, 160), repeatRows=1)
        tab.setStyle(tab_style)
        story.append(tab)
        story.append(RLSpacer(1, 1 * rl_inch))
        # end Detail section

        story.append(RLPageBreak())
        story.append(
            get_food_preperation_table(
                preperation_lines_with_incompatible_ingr, "with restrictions"
            )
        )
        story.append(RLSpacer(1, 1 * rl_inch))

        story.append(
            get_food_preperation_table(
                preperation_lines_without_incompatible_ingr, "without restrictions"
            )
        )
        story.append(RLSpacer(1, 1 * rl_inch))

        # build full document
        doc.build(story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
        return file_path

    return go()  # returns the file path


# END Kitchen count report view, helper classes and functions


def get_other_restrictions_for_meal_labels(kitchen_item):
    side_clashes = set(kitchen_item.sides_clashes)
    restr = set(kitchen_item.restricted_items)
    avoid = set(kitchen_item.avoid_ingredients)
    incompatible = set(
        ingr.replace(" (sides)", "") for ingr in kitchen_item.incompatible_ingredients
    )
    # Side clashes and incompatible ingredients were already displayed as
    # "Restrictions", we do not want to display them twice.
    return sorted((restr | avoid) - incompatible - side_clashes)


def kcr_make_labels(
    kcr_date,
    kitchen_list: Dict[int, KitchenItem],
    main_dish_name: str,
    main_dish_ingredients: str,
    sides_ingredients: str,
):
    """Generate Meal Labels sheets as a PDF file.

    Generate a label for each main dish serving to be delivered. The
    sheet format is "Avery 5162" 8,5 X 11 inches, 2 cols X 7 lines.

    Uses pylabels package - see https://github.com/bcbnz/pylabels
    and ReportLab

    Args:
        kcr_date: The delivery date of the meals.
        kitchen_list: A dictionary of KitchenItem objects (see
            order/models) which contain detailed information about
            all the meals that have to be prepared for the day and
            the client requirements and restrictions.
        main_dish_name: A string, the name of the main dish.
        main_dish_ingredient: A string, the comma separated list
            of all the ingredients in the main dish.

    Returns:
        An integer : The number of labels generated.
    """
    # dimensions are in millimeters; 1 inch = 25.4 mm
    # Sheet format is Avery 5162 : 2 columns * 7 rows
    sheet_height = 11.0 * 25.4
    sheet_width = 8.5 * 25.4
    vertic_margin = 21.0
    horiz_margin = 4.0
    columns = 2
    rows = 7
    gutter = 3.0 / 16.0 * 25.4
    specs = labels.Specification(
        sheet_width=sheet_width,
        sheet_height=sheet_height,
        columns=columns,
        rows=rows,
        column_gap=gutter,
        label_width=(sheet_width - 2.0 * horiz_margin - gutter) / columns,
        label_height=(sheet_height - 2.0 * vertic_margin) / rows,
        top_margin=vertic_margin,
        bottom_margin=vertic_margin,
        left_margin=horiz_margin,
        right_margin=horiz_margin,
        corner_radius=1.5,
    )

    sheet = labels.Sheet(specs, draw_label, border=False)

    meal_labels: list[MealLabel] = []
    for kititm in kitchen_list.values():
        meal_label = MealLabel(*meal_label_fields[1::2])
        meal_label = meal_label._replace(
            route=kititm.routename.upper(),
            date="{}".format(kcr_date.strftime("%a, %b-%d")),
            main_dish_name=main_dish_name,
            name=kititm.lastname + ", " + kititm.firstname[0:2] + ".",
        )
        if kititm.meal_size == SIZE_CHOICES_LARGE:
            meal_label = meal_label._replace(size=ugettext("LARGE"))
        if kititm.incompatible_ingredients:
            other_restr = get_other_restrictions_for_meal_labels(kititm)
            meal_label = meal_label._replace(
                main_dish_name="_______________________________________",
                dish_clashes=textwrap.wrap(
                    ugettext("Restrictions")
                    + ": {}.".format(", ".join(kititm.incompatible_ingredients)),
                    width=65,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                if kititm.incompatible_ingredients
                else "",
                other_restrictions=textwrap.wrap(
                    ugettext("Other restr.") + ": {}.".format(", ".join(other_restr)),
                    width=65,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                if other_restr
                else "",
            )
        elif not kititm.sides_clashes:
            meal_label = meal_label._replace(
                ingredients=textwrap.wrap(
                    ugettext("Ingredients") + f": {main_dish_ingredients}",
                    width=74,
                    break_long_words=False,
                    break_on_hyphens=False,
                ),
            )
        if kititm.preparation:
            prefix = ugettext("Preparation") + ": "
            # wrap all text including prefix
            preparation_list = textwrap.wrap(
                prefix + " , ".join(kititm.preparation),
                width=65,
                break_long_words=False,
                break_on_hyphens=False,
            )
            # remove prefix from first line
            preparation_list[0] = preparation_list[0][len(prefix) :]
            meal_label = meal_label._replace(preparations=[prefix] + preparation_list)
        if kititm.sides_clashes:
            prefix = (
                f"{ugettext('Sides')}: _______________________ {ugettext('Clashes')}: "
            )
            # wrap all text including prefix
            sides_clashes_list = textwrap.wrap(
                prefix + " , ".join(kititm.sides_clashes),
                width=65,
                break_long_words=False,
                break_on_hyphens=False,
            )
            # remove prefix from first line
            sides_clashes_list[0] = sides_clashes_list[0][len(prefix) :]
            meal_label = meal_label._replace(
                sides_clashes=[prefix] + sides_clashes_list
            )
        else:
            meal_label = meal_label._replace(
                sides=textwrap.wrap(
                    ugettext("Sides") + f": {sides_ingredients}",
                    width=74,
                    break_long_words=False,
                    break_on_hyphens=False,
                ),
            )

        for _j in range(1, kititm.meal_qty + 1):
            meal_labels.append(meal_label)

    # find max lengths of fields to sort on
    routew = 0
    namew = 0
    for label in meal_labels:
        routew = max(routew, len(label.route))
        namew = max(namew, len(label.name))
    # generate grouping and sorting key
    for j in range(len(meal_labels)):
        route = ""  # for groups 1, 2 and 3 : sort by name
        if meal_labels[j].dish_clashes:  # has dish restrictions
            group = 1
        elif meal_labels[j].sides_clashes:  # has sides restrictions
            group = 2
        elif meal_labels[j].preparations:  # has food preparations
            group = 3
        else:  # regular meal
            group = 4
            route = meal_labels[j].route  # sort by route, name
        meal_labels[j] = meal_labels[j]._replace(
            sortkey="{grp:1}{rou:{rouw}}{nam:{namw}}".format(
                grp=group, rou=route, rouw=routew, nam=meal_labels[j].name, namw=namew
            )
        )
    # generate labels into PDF
    for label in sorted(meal_labels, key=lambda x: x.sortkey):
        sheet.add_label(label)

    file_path = None
    if sheet.label_count > 0:
        file_path = get_meals_label_file_path(kcr_date)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(str(file_path))
    return file_path


# END Meal labels


# Delivery route sheet view, helper classes and functions.


class DeliveryRouteSheet(LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = "sous_chef.read"

    def get(self, request, **kwargs):
        delivery_date = date.fromisoformat(request.GET["delivery_date"])
        delivery_history = get_object_or_404(
            DeliveryHistory, route__pk=kwargs["pk"], date=delivery_date
        )
        route_list = Order.get_delivery_list(delivery_date, delivery_history.route_id)
        route_list = sort_sequence_ids(route_list, delivery_history.client_id_sequence)
        summary_lines, detail_lines = drs_make_lines(route_list)
        return render(
            request,
            "route_sheet.html",
            {
                "delivery_date": delivery_date,
                "detail_lines": detail_lines,
                "route": delivery_history.route,
                "summary_lines": summary_lines,
            },
        )


@dataclass
class RouteSummaryLine:
    component_group: str
    component_group_trans: str
    rqty: int
    lqty: int


def drs_make_lines(route_list: Dict[int, DeliveryClient]):
    # generate all the lines for the delivery route sheet

    summary_lines: Dict[str, RouteSummaryLine] = {}
    for _k, item in route_list.items():
        for delivery_item in item.delivery_items:
            component_group = delivery_item.component_group
            if component_group:
                line = summary_lines.setdefault(
                    component_group,
                    RouteSummaryLine(
                        component_group,
                        # find the translated name of the component group
                        next(
                            cg
                            for cg in COMPONENT_GROUP_CHOICES
                            if cg[0] == component_group
                        )[1],
                        rqty=0,
                        lqty=0,
                    ),
                )
                if (
                    component_group == COMPONENT_GROUP_CHOICES_MAIN_DISH
                    and delivery_item.size == SIZE_CHOICES_LARGE
                ):
                    line.lqty = line.lqty + delivery_item.total_quantity
                elif component_group != "":
                    line.rqty = line.rqty + delivery_item.total_quantity

    summary_lines_sorted = sorted(summary_lines.values(), key=component_group_sorting)
    return summary_lines_sorted, list(route_list.values())


def sort_sequence_ids(unordered_dic, seq):
    """Sort items in a dictionary according to a sequence of keys.

    Build an ordered dictionary using ordering of keys in 'seq' but
    ignoring the keys in 'seq' that are not in 'unordered_dic'.

    Args:
        unordered_dic : dictionary for which some keys may be absent from 'seq'
        seq : list of keys that may not all be entries in 'dic'

    Returns:
        A ordered dictionary : collections.OrderedDict()
    """
    od = collections.OrderedDict()
    if seq:
        for k in seq:
            if unordered_dic.get(k):
                od[k] = None
    # place all values from unordered_dic into ordered dict;
    #   keys not in seq will be added at the end.
    for k, val in unordered_dic.items():
        od[k] = val
    return od


# END Delivery route sheet view, helper classes and functions


def calculateRoutePointsEuclidean(data):
    """Find shortest path for points on route assuming 2D plane.

    Since the
    https://www.mapbox.com/api-documentation/#retrieve-a-duration-matrix
    endpoint is not yet available, we solve an approximation of the
    problem by assuming the world is flat and has no obstacles (2D
    Euclidean plane). This should still give good results.

    Args:
        data : A list of waypoints for leaflet.js

    Returns:
        An optimized list of waypoints.
    """
    node_to_waypoint = {}
    nodes = [
        tsp.Node(
            None,
            DELIVERY_STARTING_POINT_LAT_LONG[0],
            DELIVERY_STARTING_POINT_LAT_LONG[1],
        )
    ]
    for waypoint in data:
        node = tsp.Node(
            waypoint["id"], float(waypoint["latitude"]), float(waypoint["longitude"])
        )
        node_to_waypoint[node] = waypoint
        nodes.append(node)
    # Optimize waypoints by solving the Travelling Salesman Problem
    nodes = tsp.solve(nodes)
    # Guard against starting point which is not in node_to_waypoint
    return [node_to_waypoint[node] for node in nodes if node in node_to_waypoint]


def to_delivery_date(date_str):
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


class RefreshOrderView(LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = "sous_chef.edit"

    def post(self, request):
        delivery_date = to_delivery_date(request.POST["generateOrderDate"])
        if delivery_date and delivery_date >= datetime.now().date():
            clients = get_ongoing_clients_at_date(delivery_date)
            Order.objects.auto_create_orders(delivery_date, clients)
        else:
            print(f"RefreshOrderView: Invalid date provided: {delivery_date}")
        context = get_kitchen_count_context(delivery_date)
        return render(request, "partials/generated_orders.html", context)
