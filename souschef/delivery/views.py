import collections
import datetime
from datetime import date
import json
import os
import textwrap

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.urls import reverse_lazy, reverse
from django.contrib.admin.models import LogEntry, ADDITION
from django.db.models.functions import Lower
from django_filters.views import FilterView

import labels  # package pylabels

from reportlab.graphics import shapes as rl_shapes
from reportlab.lib import (
    colors as rl_colors, enums as rl_enums)
from reportlab.lib.styles import (
    getSampleStyleSheet as rl_getSampleStyleSheet,
    ParagraphStyle as RLParagraphStyle)
from reportlab.lib.units import inch as rl_inch
from reportlab.pdfbase import pdfmetrics as rl_pdfmetrics
from reportlab.platypus import (
    PageBreak as RLPageBreak,
    Paragraph as RLParagraph,
    SimpleDocTemplate as RLSimpleDocTemplate,
    Spacer as RLSpacer,
    Table as RLTable,
    TableStyle as RLTableStyle)

from souschef.meal.models import (
    COMPONENT_GROUP_CHOICES,
    COMPONENT_GROUP_CHOICES_MAIN_DISH,
    COMPONENT_GROUP_CHOICES_SIDES,
    Component,
    Menu, Menu_component,
    Component_ingredient)
from souschef.member.models import Client, Route, DeliveryHistory
from souschef.order.models import (
    Order, component_group_sorting, SIZE_CHOICES_REGULAR, SIZE_CHOICES_LARGE)
from .filters import KitchenCountOrderFilter
from .forms import DishIngredientsForm
from . import tsp


class Orderlist(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    # Display all the order on a given day
    context_object_name = 'orders'
    filterset_class = KitchenCountOrderFilter
    model = Order
    permission_required = 'sous_chef.read'
    template_name = 'review_orders.html'

    def get_queryset(self):
        queryset = Order.objects.get_shippable_orders().order_by(
            'client__route__pk', 'pk'
        ).prefetch_related('orders').select_related(
            'client__member',
            'client__route',
            'client__member__address'
        ).only(
            'delivery_date',
            'status',
            'client__member__firstname',
            'client__member__lastname',
            'client__route__name',
            'client__member__address__latitude',
            'client__member__address__longitude'
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super(Orderlist, self).get_context_data(**kwargs)
        context['orders_refresh_date'] = None
        if LogEntry.objects.exists():
            log = LogEntry.objects.latest('action_time')
            context['orders_refresh_date'] = log

        return context


class MealInformation(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    # Choose today's main dish and its ingredients
    permission_required = 'sous_chef.read'

    def get(self, request, **kwargs):
        # Display today's main dish and its ingredients

        #  get sides component
        try:
            sides_component = Component.objects.get(
                component_group=COMPONENT_GROUP_CHOICES_SIDES)
        except Component.DoesNotExist:
            raise Exception(
                "The database must contain exactly one component " +
                "having 'Component group' = 'Sides' ")

        date = datetime.date.today()
        main_dishes = Component.objects.order_by(Lower('name')).filter(
            component_group=COMPONENT_GROUP_CHOICES_MAIN_DISH)

        if 'id' in kwargs:
            # today's main dish has been chosen by user (onchange)
            main_dish = Component.objects.get(id=int(kwargs['id']))
            # delete all existing ingredients for the date except for sides
            Component_ingredient.objects. \
                filter(date=date). \
                exclude(component=sides_component). \
                delete()
        else:
            # see if a menu exists for today
            menu_comps = Menu_component.objects.filter(
                menu__date=date,
                component__component_group=COMPONENT_GROUP_CHOICES_MAIN_DISH)
            if menu_comps:
                # main dish is known in today's menu
                main_dish = menu_comps[0].component
            else:
                # take first main dish
                main_dish = main_dishes[0]

        recipe_ingredients = Component.get_recipe_ingredients(
            main_dish.id)
        # see if existing chosen ingredients for the main dish
        dish_ingredients = Component.get_day_ingredients(
            main_dish.id, date)
        # see if existing chosen ingredients for the sides
        sides_ingredients = Component.get_day_ingredients(
            sides_component.id, date)
        # need this for restore button
        recipe_changed = (
            len(dish_ingredients) > 0 and
            set(dish_ingredients) != set(recipe_ingredients)
        )
        # need this for update ingredients button
        ingredients_changed = (
            len(dish_ingredients) == 0 or
            len(sides_ingredients) == 0
        )

        if not dish_ingredients:
            # get recipe ingredients for the main dish
            dish_ingredients = recipe_ingredients
        form = DishIngredientsForm(
            initial={
                'maindish': main_dish.id,
                'ingredients': dish_ingredients,
                'sides_ingredients': sides_ingredients})
        # The form should be read-only if the user does not have the
        # permission to edit data.
        if not request.user.has_perm('sous_chef.edit'):
            [setattr(form.fields[k], 'disabled', True) for k in form.fields]

        return render(
            request,
            'ingredients.html',
            {'form': form,
             'date': str(date),
             'recipe_changed': recipe_changed,
             'ingredients_changed': ingredients_changed}
        )

    def post(self, request):
        # Choose ingredients in today's main dish and in Sides

        # Prevent users to go further if they don't have the permission
        # to edit data.
        if not request.user.has_perm('sous_chef.edit'):
            raise PermissionDenied

        # print("Pick Ingredients POST request=", request.POST)  # For DEBUG
        date = datetime.date.today()
        form = DishIngredientsForm(request.POST)
        # get sides component
        try:
            sides_component = Component.objects.get(
                component_group=COMPONENT_GROUP_CHOICES_SIDES)
        except Component.DoesNotExist:
            raise Exception(
                "The database must contain exactly one component " +
                "having 'Component group' = 'Sides' ")

        if '_restore' in request.POST:
            # restore ingredients of main dish to those in recipe
            # delete all existing ingredients for the date except for sides
            Component_ingredient.objects. \
                filter(date=date). \
                exclude(component=sides_component). \
                delete()
            return HttpResponseRedirect(
                reverse_lazy("delivery:meal"))
        elif '_update' in request.POST:
            # update ingredients of main dish and ingredients of sides
            if form.is_valid():
                ingredients = form.cleaned_data['ingredients']
                sides_ingredients = form.cleaned_data['sides_ingredients']
                component = form.cleaned_data['maindish']
                # delete all main dish and sides ingredients for the date
                Component_ingredient.objects.filter(date=date).delete()
                # add revised ingredients for the date + dish
                for ing in ingredients:
                    ci = Component_ingredient(
                        component=component,
                        ingredient=ing,
                        date=date)
                    ci.save()
                # add revised ingredients for the date + sides
                for ing in sides_ingredients:
                    ci = Component_ingredient(
                        component=sides_component,
                        ingredient=ing,
                        date=date)
                    ci.save()
                # Create menu and its components for today
                compnames = [component.name]  # main dish
                # take first sorted name of each other component group
                for group, ignore in COMPONENT_GROUP_CHOICES:
                    if group != COMPONENT_GROUP_CHOICES_MAIN_DISH:
                        compname = Component.objects.order_by(
                            Lower('name')).filter(
                                component_group=group
                            )
                        if compname:
                            compnames.append(compname[0].name)
                Menu.create_menu_and_components(date, compnames)
                return HttpResponseRedirect(
                    reverse_lazy("delivery:meal"))
        # END IF
        return render(
            request,
            'ingredients.html',
            {'form': form,
             'date': str(date),
             'recipe_changed': False,
             'ingredients_changed': True}
        )


class RoutesInformation(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    """Display route list page or download the route sheets report.

    Display all the route information for a given day.

    The view must first determine whether each of the routes with orders
    has been "organized by the user".

    By default the view displays a list of all the known routes
    indicating for each route the number of orders today and its
    organize state. The view then creates the context to be rendered
    on the page.

    If the request includes argument "print=yes", the view obtains
    for each route the detailed orders to be delivered, sorts them in the
    chosen sequence and combines all the routes in a PDF report that
    is stored in the BASE_DIR and then downloaded by the browser.
    """
    permission_required = 'sous_chef.read'

    @property
    def doprint(self):
        return self.request.GET.get('print', False)

    def get(self, request, *args, **kwargs):
        routes = Route.objects.all()
        route_details = []
        all_configured = True
        for route in routes:
            clients = Order.objects.get_shippable_orders_by_route(
                route.id, exclude_non_geolocalized=True).values_list(
                    'client__pk', flat=True)
            order_count = len(clients)
            try:
                delivery_history = DeliveryHistory.objects.get(
                    route=route,
                    date=timezone.datetime.today()
                )
                set1 = set(delivery_history.client_id_sequence)
                set2 = set(clients)
                has_organised = 'yes' if set1 == set2 else 'invalid'
            except DeliveryHistory.DoesNotExist:
                delivery_history = None
                has_organised = 'no'
            except TypeError:
                # `client_id_sequence` is not iterable.
                has_organised = 'invalid'

            route_details.append(
                (route, order_count, has_organised, delivery_history)
            )
            if order_count > 0 and has_organised != 'yes':
                all_configured = False

        if not self.doprint:
            # display list of delivery routes on web page
            return render(request, 'routes.html',
                          {'route_details': route_details,
                           'all_configured': all_configured})
        else:
            # download route sheets report as PDF
            if not all_configured:
                raise Http404
            today = timezone.datetime.today()
            routes_dict = {}
            for delivery_history in DeliveryHistory.objects.filter(
                    date=today
            ):
                route_list = Order.get_delivery_list(
                    today, delivery_history.route_id
                )
                route_list = sort_sequence_ids(
                    route_list, delivery_history.client_id_sequence
                )
                summary_lines, detail_lines = drs_make_lines(route_list)
                routes_dict[delivery_history.route_id] = {
                    'route': delivery_history.route,
                    'summary_lines': summary_lines,
                    'detail_lines': detail_lines
                }
            # generate PDF report
            MultiRouteReport.routes_make_pages(routes_dict)
            try:
                f = open(settings.ROUTE_SHEETS_FILE, "rb")
            except Exception:
                raise Http404("File " + settings.ROUTE_SHEETS_FILE + " does not exist")
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = \
                'attachment; filename="routesheets{}.pdf"'. \
                format(datetime.date.today().strftime("%Y%m%d"))
            # add serializable data in response header to be used in unit tests
            routes_dict_fortest = {}
            for key, item in routes_dict.items():
                routes_dict_fortest[key] = {
                    'route': item['route'].name,
                    'detail_lines': [client.lastname
                                     for client in item['detail_lines']],
                }
            response['routes_dict'] = json.dumps(routes_dict_fortest)
            #
            response.write(f.read())
            f.close()
            return response


class CreateDeliveryOfToday(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = 'sous_chef.edit'

    def post(self, request, pk, *args, **kwargs):
        route = get_object_or_404(Route, pk=pk)
        if not Order.objects.get_shippable_orders_by_route(
                route.id, exclude_non_geolocalized=True).exists():
            # No clients on this route.
            raise Http404

        try:
            DeliveryHistory.objects.get(
                route=route, date=timezone.datetime.today()
            )
        except DeliveryHistory.DoesNotExist:
            DeliveryHistory.objects.create(
                route=route, date=timezone.datetime.today(),
                vehicle=route.vehicle
            )
        return HttpResponseRedirect(
            reverse('delivery:edit_delivery_of_today', kwargs={'pk': pk})
        )


class EditDeliveryOfToday(
        LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView):
    model = DeliveryHistory
    fields = ('vehicle', 'client_id_sequence', 'comments')
    permission_required = 'sous_chef.edit'
    template_name = 'edit_delivery_of_today.html'

    def get_object(self, *args, **kwargs):
        return get_object_or_404(
            DeliveryHistory.objects.select_related('route'),
            route=self.kwargs.get('pk'),
            date=timezone.datetime.today()
        )

    def get_context_data(self, **kwargs):
        context = super(EditDeliveryOfToday, self).get_context_data(**kwargs)
        context['delivery_history'] = self.object
        # This needs to be placed on the top when refactoring Route module.
        # It causes circular dependancy in current code structure.
        from souschef.member.views import get_clients_on_delivery_history  # noqa
        context['clients_on_delivery_history'] = (
            get_clients_on_delivery_history(
                self.object,
                func_add_warning_message=lambda m: messages.add_message(
                    self.request, messages.ERROR, m)
            )
        )
        return context

    def get_success_url(self):
        return reverse_lazy('delivery:routes')

    def form_valid(self, form):
        response = super(EditDeliveryOfToday, self).form_valid(form)
        messages.add_message(
            self.request, messages.SUCCESS,
            _("Today's delivery on route %(route_name)s has been updated.") % {
                'route_name': self.object.route.name
            }
        )
        return response


# Route sheet report classes and functions.

def defineStyles(my_styles):
    """Define common styles for ReportLab objects.

    Adds reportlab.lib.styles.ParagraphStyle objects to my_styles.

    Args:
        my_styles: A reportlab.lib.styles.StyleSheet1 object.
    """
    my_styles.add(RLParagraphStyle(
        name='SmallRight', fontName='Helvetica',
        fontSize=7, alignment=rl_enums.TA_RIGHT))

    my_styles.add(RLParagraphStyle(
        name='NormalLeft', fontName='Helvetica',
        fontSize=10, alignment=rl_enums.TA_LEFT))
    my_styles.add(RLParagraphStyle(
        name='NormalLeftBold', fontName='Helvetica-Bold',
        fontSize=10, alignment=rl_enums.TA_LEFT))
    my_styles.add(RLParagraphStyle(
        name='NormalCenter', fontName='Helvetica',
        fontSize=10, alignment=rl_enums.TA_CENTER))
    my_styles.add(RLParagraphStyle(
        name='NormalCenterBold', fontName='Helvetica-Bold',
        fontSize=10, alignment=rl_enums.TA_CENTER))
    my_styles.add(RLParagraphStyle(
        name='NormalRight', fontName='Helvetica',
        fontSize=10, alignment=rl_enums.TA_RIGHT))
    my_styles.add(RLParagraphStyle(
        name='NormalRightBold', fontName='Helvetica-Bold',
        fontSize=10, alignment=rl_enums.TA_RIGHT))

    my_styles.add(RLParagraphStyle(
        name='LargeLeft', fontName='Helvetica',
        fontSize=12, alignment=rl_enums.TA_LEFT))
    my_styles.add(RLParagraphStyle(
        name='LargeCenter', fontName='Helvetica',
        fontSize=12, alignment=rl_enums.TA_CENTER))
    my_styles.add(RLParagraphStyle(
        name='LargeRight', fontName='Helvetica',
        fontSize=12, alignment=rl_enums.TA_RIGHT))
    my_styles.add(RLParagraphStyle(
        name='LargeBoldLeft', fontName='Helvetica-Bold',
        fontSize=12, alignment=rl_enums.TA_LEFT))
    my_styles.add(RLParagraphStyle(
        name='LargeBoldRight', fontName='Helvetica-Bold',
        fontSize=12, alignment=rl_enums.TA_RIGHT))

    my_styles.add(RLParagraphStyle(
        name='VeryLargeBoldLeft', fontName='Helvetica-Bold',
        fontSize=14, alignment=rl_enums.TA_LEFT,
        spaceAfter=5))

    my_styles.add(RLParagraphStyle(
        name='HugeBoldCenter', fontName='Helvetica-Bold',
        fontSize=20, alignment=rl_enums.TA_CENTER))


class MultiRouteReport(object):
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
        """Custom table for route sheets that is monitored for table splits.
        """
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
        """Custom document template for route sheets having multiple tables.

        """
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
                self.footerFunc = kwargs.pop('footerFunc')
            except KeyError:
                raise KeyError(self.__class__.__name__ +
                               " missing kwarg : footerFunc")
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
                if (self.page -
                        MultiRouteReport.route_start_page + 1) % 2 != 0:
                    # split occured at bottom of front side of sheet (odd page)
                    self.footerFunc(
                        self,
                        '** SUITE AU VERSO / CONTINUED ON REVERSE SIDE **')
                else:
                    # split occured at bottom of back side of sheet (even page)
                    self.footerFunc(
                        self,
                        '** VOIR FEUILLE SUIVANTE / SEE NEXT SHEET **')
            else:
                # no table split means route finishes on this page
                if (self.page -
                        MultiRouteReport.route_start_page + 1) % 2 != 0:
                    # route finishes on odd page, add a blank page
                    self.canv.showPage()
                # the next route, if any, will start on next document page
                MultiRouteReport.route_start_page = self.page + 1

    # static method
    def routes_make_pages(routes_dict):
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
            canvas.setFont('Helvetica-Bold', 12)
            canvas.drawString(
                x=1.5 * rl_inch, y=PAGE_HEIGHT + 0.30 * rl_inch,
                text='Santropol Roulant')
            canvas.setFont('Helvetica', 12)
            canvas.drawString(
                x=1.5 * rl_inch, y=PAGE_HEIGHT + 0.15 * rl_inch,
                text='Tel. : (514) 284-9335')
            canvas.setFont('Helvetica', 10)
            canvas.drawString(
                x=1.5 * rl_inch, y=PAGE_HEIGHT - 0.0 * rl_inch,
                text='{}'.format(
                    datetime.date.today().strftime('%a., %d %B %Y')))
            canvas.drawString(
                x=3.25 * rl_inch, y=PAGE_HEIGHT + 0.30 * rl_inch,
                text='(Ce document contient des informations CONFIDENTIELLES.)'
            )
            canvas.drawString(
                x=3.25 * rl_inch, y=PAGE_HEIGHT + 0.15 * rl_inch,
                text='(This document contains CONFIDENTIAL information.)')
            canvas.drawRightString(
                x=PAGE_WIDTH - 0.75 * rl_inch, y=PAGE_HEIGHT + 0.30 * rl_inch,
                text='Page {:d}'.format(
                    doc.page - MultiRouteReport.route_start_page + 1))
            canvas.drawInlineImage(
                settings.LOGO_IMAGE,
                0.5 * rl_inch, PAGE_HEIGHT - 0.2 * rl_inch,
                width=0.8 * rl_inch, height=0.7 * rl_inch)
            canvas.restoreState()

        def drawFooter(doc, text):
            """Draw the page footer.

            Args:
                doc : A reportlab.platypus.SimpleDocTemplate object.
                text : A string to place in the footer.
            """
            doc.canv.saveState()
            doc.canv.setFont('Helvetica', 14)
            doc.canv.drawCentredString(
                x=4.0 * rl_inch,
                y=PAGE_HEIGHT - 10.5 * rl_inch,
                text=text)
            doc.canv.restoreState()

        def go():
            """Generate the pages.

            Returns:
                An integer : The number of pages generated.
            """
            doc = MultiRouteReport.RLMultiRouteDocTemplate(
                settings.ROUTE_SHEETS_FILE,
                leftMargin=0.5 * rl_inch,
                rightMargin=0.5 * rl_inch,
                bottomMargin=0.5 * rl_inch,
                footerFunc=drawFooter)
            # initialize
            MultiRouteReport.table_split = 0
            MultiRouteReport.document = doc
            MultiRouteReport.route_start_page = 1
            story = []
            first_route = True

            # TODO Loop over routes
            for route in routes_dict.values():
                if not route['summary_lines']:
                    # empty route : skip it
                    continue
                # begin Summary section
                if not first_route:
                    # next route must start on a new page
                    story.append(RLPageBreak())
                rows = []
                rows.append(
                    [RLParagraph('PLAT / DISH', styles['NormalLeftBold']),
                     RLParagraph('Qté / Qty', styles['NormalCenterBold'])])
                for sl in route['summary_lines']:
                    rows.append([RLParagraph(sl.component_group_trans,
                                             styles['NormalLeft']),
                                 RLParagraph(str(sl.rqty + sl.lqty),
                                             styles['NormalCenter'])])
                tab = MultiRouteReport.RLMultiRouteTable(
                    rows,
                    colWidths=(100, 60),
                    style=[('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('GRID', (0, 0), (-1, -1), 1, rl_colors.black),
                           ('ALIGN', (0, 0), (-1, -1), 'RIGHT')],
                    hAlign='LEFT')
                story.append(tab)
                # end Summary section

                # Route name
                story.append(RLSpacer(1, 0.25 * rl_inch))
                story.append(RLParagraph(route['route'].name,
                                         styles['HugeBoldCenter']))
                story.append(RLSpacer(1, 0.25 * rl_inch))
                story.append(RLParagraph('- DÉBUT DE LA ROUTE / START ROUTE -',
                                         styles['LargeLeft']))
                story.append(RLSpacer(1, 0.125 * rl_inch))

                # begin Detail section
                rows = []
                line = 0
                tab_style = RLTableStyle(
                    [('VALIGN', (0, 0), (-1, -1), 'TOP')])
                rows.append([RLParagraph('Client', styles['NormalLeft']),
                             RLParagraph('Note', styles['NormalLeft']),
                             RLParagraph('Items', styles['NormalLeft']),
                             RLParagraph('', styles['NormalLeft'])])
                tab_style.add('LINEABOVE',
                              (0, 0), (-1, 0), 1, rl_colors.black)
                line += 1
                for c in route['detail_lines']:
                    tab_style.add('LINEABOVE',
                                  (0, line), (-1, line), 1, rl_colors.black)
                    rows.append([
                        # client
                        [RLParagraph(c.firstname + ' ' + c.lastname,
                                     styles['VeryLargeBoldLeft']),
                         RLParagraph(c.street,
                                     styles['LargeLeft']),
                         RLParagraph(
                             'Apt ' + c.apartment,
                             styles['LargeLeft']) if c.apartment else [],
                         RLParagraph(c.phone,
                                     styles['LargeLeft'])],
                        # note
                        RLParagraph(c.delivery_note,
                                    styles['LargeLeft']),
                        # items
                        ([RLParagraph(i.component_group_trans,
                                      styles['LargeLeft'])
                          for i in c.delivery_items] +
                         [RLParagraph("Facture / Bill",
                                      styles['LargeLeft'])
                          if c.include_a_bill else []]),
                        # quantity
                        [RLParagraph(str(i.total_quantity),
                                     styles['LargeRight'])
                         for i in c.delivery_items]])
                    line += 1
                # END for
                # add row for number of clients
                rows.append([
                    [RLParagraph("- FIN DE LA ROUTE -", styles['LargeLeft']),
                     RLParagraph("- END OF ROUTE- ", styles['LargeLeft'])],
                    [RLParagraph("Nombre d'arrêts :", styles['LargeRight']),
                     RLParagraph("Number of Stops :", styles['LargeRight'])],
                    RLParagraph(str(line - 1), styles['LargeLeft']),
                    RLParagraph("", styles['LargeLeft'])])
                #
                tab_style.add('LINEBELOW',
                              (0, line - 1), (-1, line - 1), 1,
                              rl_colors.black)
                tab = MultiRouteReport.RLMultiRouteTable(
                              rows,
                              colWidths=(140, 255, 100, 20),
                              repeatRows=1)
                tab.setStyle(tab_style)
                story.append(tab)
                # end Detail section
                first_route = False
            # END for

            # build full document
            doc.build(story,
                      onFirstPage=drawHeader, onLaterPages=drawHeader)
            return doc.page  # number of last page
        # END def

        return go()  # returns number of pages generated

# END Route sheet report.


# Kitchen count report view, helper classes and functions

class KitchenCount(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = 'sous_chef.read'

    def get(self, request, *args, **kwargs):
        if reverse('delivery:downloadKitchenCount') in request.path:
            # download kitchen count report as PDF
            try:
                f = open(settings.KITCHEN_COUNT_FILE, "rb")
            except Exception:
                raise Http404("File " + settings.KITCHEN_COUNT_FILE + " does not exist")
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = \
                'attachment; filename="kitchencount{}.pdf"'. \
                format(datetime.date.today().strftime("%Y%m%d"))
            response.write(f.read())
            f.close()
            return response
        else:
            # Display kitchen count report for given delivery date
            #   or for today by default; generate meal labels
            if 'year' in kwargs and 'month' in kwargs and 'day' in kwargs:
                date = datetime.date(
                    int(kwargs['year']), int(kwargs['month']),
                    int(kwargs['day']))
            else:
                date = datetime.date.today()
            #  get sides component
            try:
                sides_component = Component.objects.get(
                    component_group=COMPONENT_GROUP_CHOICES_SIDES)
            except Component.DoesNotExist:
                raise Exception(
                    "The database must contain exactly one component " +
                    "having 'Component group' = 'Sides' ")
            # check if main dish ingredients were confirmed
            main_ingredients = Component_ingredient.objects. \
                filter(date=date). \
                exclude(component=sides_component)
            # check if sides ingredients were confirmed
            sides_ingredients = Component_ingredient.objects. \
                filter(component=sides_component, date=date)
            if len(main_ingredients) == 0 or len(sides_ingredients) == 0:
                # some ingredients not confirmed, must go back one step
                messages.add_message(
                    self.request, messages.WARNING,
                    _("Please check main dish and confirm" +
                      " all ingredients before proceeding to kitchen count")
                )
                return HttpResponseRedirect(
                    reverse_lazy("delivery:meal"))

            kitchen_list_unfiltered = Order.get_kitchen_items(date)

            # filter out route=None clients and not geolocalized clients
            kitchen_list = {}
            geolocalized_client_ids = list(Client.objects.filter(
                pk__in=kitchen_list_unfiltered.keys(),
                member__address__latitude__isnull=False,
                member__address__longitude__isnull=False
            ).values_list('pk', flat=True))

            for client_id, kitchen_item in kitchen_list_unfiltered.items():
                if kitchen_item.routename is not None \
                   and client_id in geolocalized_client_ids:
                    kitchen_list[client_id] = kitchen_item

            component_lines, meal_lines = kcr_make_lines(kitchen_list, date)
            if component_lines:
                # we have orders today
                num_pages = kcr_make_pages(     # kitchen count as PDF
                    date,
                    component_lines,                    # summary
                    meal_lines)                         # detail
                num_labels = kcr_make_labels(   # meal labels as PDF
                    date,
                    kitchen_list,                       # KitchenItems
                    component_lines[0].name,            # main dish name
                    component_lines[0].ingredients)     # main dish ingredients
            else:
                # no orders today
                num_pages = 0
                num_labels = 0
            return render(request, 'kitchen_count.html',
                          {'component_lines': component_lines,
                           'meal_lines': meal_lines,
                           'num_pages': num_pages,
                           'num_labels': num_labels})


component_line_fields = [          # Component summary Line on Kitchen Count.
    # field name       default value
    'component_group', '',    # ex. main dish, dessert etc
    'rqty', 0,     # Quantity of regular size main dishes
    'lqty', 0,     # Quantity of large size main dishes
    'name', '',    # String : component name
    'ingredients'      '']    # String : today's ingredients in main dish
ComponentLine = collections.namedtuple(
    'ComponentLine', component_line_fields[0::2])


meal_line_fields = [               # Special Meal Line on Kitchen Count.
    # field name       default value
    'client', '',     # String : Lastname and abbreviated first name
    'rqty', '',     # String : Quantity of regular size main dishes
    'lqty', '',     # String : Quantity of large size main dishes
    'ingr_clash', '',     # String : Ingredients that clash
    'rest_ingr', '',     # String : Other ingredients to avoid
    'rest_item', '',     # String : Restricted items
    'span', '1']   # Number of lines to "rowspan" in table
MealLine = collections.namedtuple(
    'MealLine', meal_line_fields[0::2])


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
        client=kititm.lastname + ', ' + kititm.firstname[0:2] + '.',
        rqty=(str(kititm.meal_qty)
              if kititm.meal_size == SIZE_CHOICES_REGULAR else ''),
        lqty=(str(kititm.meal_qty)
              if kititm.meal_size == SIZE_CHOICES_LARGE else ''),
        ingr_clash='',
        rest_ingr=', '.join(
            sorted(list(set(kititm.avoid_ingredients) -
                        set(kititm.incompatible_ingredients)))),
        rest_item=', '.join(kititm.restricted_items),
        span='1')


def kcr_cumulate(regular, large, meal):
    """Count cumulative meal quantities by size.

    Based on the size and on the number of servings of the 'meal',
    calculate the new cumulative quantities by size.

    Args:
        regular : carried over quantity of regular size main dishes.
        large : carried over quantity of large size main dishes.
        meal : MealLine object

    Returns:
        A tuple of the new cumulative quantities : (regular, large)
    """
    if meal.meal_size == SIZE_CHOICES_REGULAR:
        regular = regular + meal.meal_qty
    else:
        large = large + meal.meal_qty
    return (regular, large)


def kcr_make_lines(kitchen_list, date):
    """Generate the sections and lines for the kitchen count report.

    Count all the dishes that have to be prepared and identify all the
    special client requirements such as disliked ingredients and
    restrictions.

    Args:
        kitchen_list : A dictionary of KitchenItem objects (see
            order/models) which contain detailed information about
            all the meals that have to be prepared for the day and
            the client requirements and restrictions.
        date : A date.datetime object giving the date on which the
            meals will be delivered.

    Returns:
        A tuple. First value is the component (dishes) summary lines. The
          second value is the special meals lines.
    """
    # Build component summary
    component_lines = {}
    for k, item in kitchen_list.items():
        for component_group, meal_component \
                in item.meal_components.items():
            component_lines.setdefault(
                component_group,
                ComponentLine(
                    # find the translated name of the component group
                    component_group=next(cg for cg in COMPONENT_GROUP_CHOICES
                                         if cg[0] == component_group)[1],
                    rqty=0,
                    lqty=0,
                    name='',
                    ingredients=''))
            if (component_group == COMPONENT_GROUP_CHOICES_MAIN_DISH and
                    component_lines[component_group].name == ''):
                # not yet got main dish name and ingredients, do it
                component_lines[component_group] = \
                    component_lines[component_group]._replace(
                        name=meal_component.name,
                        ingredients=", ".join(
                            [ing.name for ing in
                             Component.get_day_ingredients(
                                 meal_component.id, date)]))
            if (component_group == COMPONENT_GROUP_CHOICES_MAIN_DISH and
                    item.meal_size == SIZE_CHOICES_LARGE):
                component_lines[component_group] = \
                    component_lines[component_group]._replace(
                        lqty=(component_lines[component_group].lqty +
                              meal_component.qty))
            else:
                component_lines[component_group] = \
                    component_lines[component_group]._replace(
                        rqty=(component_lines[component_group].rqty +
                              meal_component.qty))
        # END FOR
    # END FOR
    # Sort component summary
    items = component_lines.items()
    if items:
        component_lines_sorted = \
            [component_lines[COMPONENT_GROUP_CHOICES_MAIN_DISH]]
        component_lines_sorted.extend(
            sorted([v for k, v in items if
                    k != COMPONENT_GROUP_CHOICES_MAIN_DISH],
                   key=lambda x: x.component_group))
    else:
        component_lines_sorted = []

    # Build special meal lines

    meal_lines = []
    rtotal, ltotal = (0, 0)
    # Ingredients clashes (and other columns)
    rsubtotal, lsubtotal = (0, 0)
    clients = iter(sorted(
        [(ke, val) for ke, val in kitchen_list.items() if
         val.incompatible_ingredients],
        key=lambda x: x[1].incompatible_ingredients))

    # first line of a combination of ingredients
    line_start = 0
    rsubtotal, lsubtotal = (0, 0)
    k, v = next(clients, (0, 0))  # has end sentinel
    while k > 0:
        if rsubtotal == 0 and lsubtotal == 0:
            # add line for subtotal at top of combination
            meal_lines.append(MealLine(*meal_line_fields[1::2]))
        combination = v.incompatible_ingredients
        meal_lines.append(meal_line(v))
        rsubtotal, lsubtotal = kcr_cumulate(rsubtotal, lsubtotal, v)
        k, v = next(clients, (0, 0))
        if k == 0 or combination != v.incompatible_ingredients:
            # last line of this combination of ingredients
            line_end = len(meal_lines)
            # set rowspan to total number of lines for this combination
            meal_lines[line_start] = meal_lines[line_start]._replace(
                client='SUBTOTAL',
                rqty=str(rsubtotal),
                lqty=str(lsubtotal),
                ingr_clash=', '.join(combination),
                span=str(line_end - line_start))
            rtotal, ltotal = (rtotal + rsubtotal, ltotal + lsubtotal)
            rsubtotal, lsubtotal = (0, 0)
            # hide ingredients for lines following the first
            for j in range(line_start + 1, line_end):
                meal_lines[j] = meal_lines[j]._replace(span='-1')
            # Add a blank line as separator
            meal_lines.append(MealLine(*meal_line_fields[1::2]))
            # first line of next combination of ingredients
            line_start = len(meal_lines)
    # END WHILE

    meal_lines.append(MealLine(*meal_line_fields[1::2])._replace(
        rqty=str(rtotal), lqty=str(ltotal), ingr_clash='TOTAL SPECIALS'))

    return (component_lines_sorted, meal_lines)


def kcr_make_pages(date, component_lines, meal_lines):
    """Generate the kitchen count report pages as a PDF file.

    Uses ReportLab see http://www.reportlab.com/documentation/faq/

    Args:
        date : The delivery date of the meals.
        component_lines : A list of ComponentLine objects, the summary of
            component quantities and sizes for the date's meal.
        meal_lines : A list of MealLine objects, the details of the clients
            for the date that have ingredients clashing with those in today's
            main dish.

    Returns:
        An integer : The number of pages generated.
    """
    PAGE_HEIGHT = 11.0 * rl_inch
    PAGE_WIDTH = 8.5 * rl_inch

    styles = rl_getSampleStyleSheet()
    defineStyles(styles)

    def drawHeader(canvas, doc):
        """Draw the header part common to all pages.

        Args:
            canvas : A reportlab.pdfgen.canvas.Canvas object.
            doc : A reportlab.platypus.SimpleDocTemplate object.
        """
        canvas.setFont('Helvetica', 14)
        canvas.drawString(
            x=1.9 * rl_inch, y=PAGE_HEIGHT,
            text='Kitchen count report')
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(
            x=6.0 * rl_inch, y=PAGE_HEIGHT,
            text='{}'.format(datetime.date.today().strftime('%a., %d %B %Y')))
        canvas.drawRightString(
            x=PAGE_WIDTH - 0.75 * rl_inch, y=PAGE_HEIGHT,
            text='Page {:d}'.format(doc.page))

    def myFirstPage(canvas, doc):
        """Draw the complete header for the first page.

        Args:
            canvas : A reportlab.pdfgen.canvas.Canvas object.
            doc : A reportlab.platypus.SimpleDocTemplate object.
        """
        canvas.saveState()
        drawHeader(canvas, doc)
        canvas.drawInlineImage(
            settings.LOGO_IMAGE,
            0.75 * rl_inch, PAGE_HEIGHT - 1.0 * rl_inch,
            width=1.0 * rl_inch, height=1.0 * rl_inch)
        canvas.restoreState()

    def myLaterPages(canvas, doc):
        """Draw the complete header for all pages except the first one.

        Args:
            canvas : A reportlab.pdfgen.canvas.Canvas object.
            doc : A reportlab.platypus.SimpleDocTemplate object.
        """
        canvas.saveState()
        drawHeader(canvas, doc)
        canvas.restoreState()

    def go():
        """Generate the pages.

        Returns:
            An integer : The number of pages generated.
        """
        doc = RLSimpleDocTemplate(settings.KITCHEN_COUNT_FILE)
        story = []

        # begin Summary section
        story.append(RLSpacer(1, 0.25 * rl_inch))
        rows = []
        rows.append(['',
                     RLParagraph('TOTAL', styles['NormalCenter']),
                     '',
                     RLParagraph('Menu', styles['NormalLeft']),
                     RLParagraph('Ingredients', styles['NormalLeft'])])
        rows.append(['',
                     RLParagraph('Regular', styles['SmallRight']),
                     RLParagraph('Large', styles['SmallRight']),
                     '',
                     ''])
        for cl in component_lines:
            rows.append([cl.component_group,
                         cl.rqty,
                         cl.lqty,
                         cl.name,
                         RLParagraph(cl.ingredients, styles['NormalLeft'])])
        tab = RLTable(rows,
                      colWidths=(100, 40, 40, 120, 220),
                      style=[('VALIGN', (0, 0), (-1, 1), 'TOP'),
                             ('VALIGN', (0, 2), (-1, -1), 'BOTTOM'),
                             ('GRID', (1, 0), (-1, 1), 1, rl_colors.black),
                             ('SPAN', (1, 0), (2, 0)),
                             ('ALIGN', (1, 2), (2, -1), 'RIGHT'),
                             ('SPAN', (3, 0), (3, 1)),
                             ('SPAN', (4, 0), (4, 1))])
        story.append(tab)
        story.append(RLSpacer(1, 0.25 * rl_inch))
        # end Summary section

        # begin Detail section
        rows = []
        line = 0
        tab_style = RLTableStyle(
            [('VALIGN', (0, 0), (-1, -1), 'TOP')])
        rows.append([RLParagraph('Clashing ingredients', styles['NormalLeft']),
                     RLParagraph('Regular', styles['NormalRight']),
                     RLParagraph('Large', styles['NormalRight']),
                     '',
                     RLParagraph('Client', styles['NormalLeft']),
                     RLParagraph('Other restrictions', styles['NormalLeft'])])
        tab_style.add('LINEABOVE',
                      (0, line), (-1, line), 1, rl_colors.black)
        tab_style.add('LINEBEFORE',
                      (0, line), (0, line), 1, rl_colors.black)
        tab_style.add('LINEAFTER',
                      (-1, line), (-1, line), 1, rl_colors.black)
        line += 1
        for ml in meal_lines:
            if ml.ingr_clash and not ml.client:
                # Total line at the bottom
                rows.append([RLParagraph(ml.ingr_clash,
                                         styles['NormalLeftBold']),
                             RLParagraph(ml.rqty, styles['NormalRightBold']),
                             RLParagraph(ml.lqty, styles['NormalRightBold']),
                             '',
                             '',
                             ''])
                tab_style.add('LINEABOVE',
                              (0, line), (-1, line), 1, rl_colors.black)
            elif ml.ingr_clash or ml.client:
                # not a blank separator line
                if ml.span != '-1':
                    # line has ingredient clash data
                    tab_style.add('SPAN',
                                  (0, line), (0, line + int(ml.span) - 1))
                    tab_style.add('LINEABOVE',
                                  (0, line), (-1, line), 1, rl_colors.black)
                    # for dashes, must use LINEABOVE because dashes do not work
                    #   with LINEBELOW; seems to be a bug in ReportLab see :
                    #   reportlab/platypus/tables.py line # 1309
                    tab_style.add('LINEABOVE',           # op
                                  (1, line + 1),         # start
                                  (-1, line + 1),        # stop
                                  1,                     # weight
                                  rl_colors.black,       # color
                                  None,                  # cap
                                  [1, 2])                # dashes
                    value = RLParagraph(ml.ingr_clash, styles['LargeBoldLeft'])
                else:
                    # span = -1 means clash data must be blanked out
                    #   because it is the same as the initial spanned row
                    value = ''
                # END IF
                if ml.client == 'SUBTOTAL':
                    client = ''
                    qty_style = 'LargeBoldRight'
                else:
                    client = ml.client
                    qty_style = 'NormalRight'
                rows.append([
                    value,
                    RLParagraph(ml.rqty, styles[qty_style]),
                    RLParagraph(ml.lqty, styles[qty_style]),
                    '',
                    RLParagraph(client, styles['NormalLeft']),
                    [RLParagraph(
                        ml.rest_ingr +
                        (' ;' if ml.rest_ingr and ml.rest_item else ''),
                        styles['NormalLeft']),
                     RLParagraph(ml.rest_item, styles['NormalLeftBold'])]])
                # END IF
                line += 1
            # END IF
        # END FOR
        tab = RLTable(rows,
                      colWidths=(150, 50, 50, 20, 100, 150),
                      repeatRows=1)
        tab.setStyle(tab_style)
        story.append(tab)
        story.append(RLSpacer(1, 1 * rl_inch))
        # end Detail section

        # build full document
        doc.build(story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
        return doc.page
    return go()  # returns number of pages generated

# END Kitchen count report view, helper classes and functions


# Meal labels generation data structures and functions.

meal_label_fields = [                         # Contents for Meal Labels.
    # field name, default value
    'sortkey', '',          # key for sorting
    'route', '',            # String : Route name
    'name', '',             # String : Last + First abbreviated
    'date', '',             # String : Delivery date
    'size', '',             # String : Regular or Large
    'main_dish_name', '',   # String
    'dish_clashes', [],   # List of strings
    'preparations', [],   # List of strings
    'sides_clashes', [],    # List of strings
    'other_restrictions', [],   # List of strings
    'ingredients', []]  # List of strings
MealLabel = collections.namedtuple(
    'MealLabel', meal_label_fields[0::2])


def draw_label(label, width, height, data):
    """Draw a single Meal Label on the sheet.

    Callback function that is used by the labels generator.

    Args:
        label : Object passed by pylabels.
        width : Single label width in font points.
        height : Single label height in font points.
        data : A MealLabel namedtuple.
    """
    # dimensions are in font points (72 points = 1 inch)
    # Line 1
    vertic_pos = height * 0.85
    horiz_margin = 9  # distance from edge of label 9/72 = 1/8 inch
    if data.name:
        label.add(rl_shapes.String(
            horiz_margin, vertic_pos, data.name,
            fontName="Helvetica-Bold", fontSize=12))
    if data.route:
        label.add(rl_shapes.String(
            width / 2.0, vertic_pos, data.route,
            fontName="Helvetica-Oblique", fontSize=10, textAnchor="middle"))
    if data.date:
        label.add(rl_shapes.String(
            width - horiz_margin, vertic_pos, data.date,
            fontName="Helvetica", fontSize=10, textAnchor="end"))
    # Line 2
    vertic_pos -= 14
    if data.main_dish_name:
        label.add(rl_shapes.String(
            horiz_margin, vertic_pos, data.main_dish_name,
            fontName="Helvetica-Bold", fontSize=10))
    if data.size:
        label.add(rl_shapes.String(
            width - horiz_margin, vertic_pos, data.size,
            fontName="Helvetica-Bold", fontSize=10, textAnchor="end"))
    # Line(s) 3
    vertic_pos -= 12
    if data.dish_clashes:
        for line in data.dish_clashes:
            label.add(rl_shapes.String(
                horiz_margin, vertic_pos, line,
                fontName="Helvetica", fontSize=9))
            vertic_pos -= 10
    # Line(s) 4
    if data.preparations:
        # draw prefix
        label.add(rl_shapes.String(
            horiz_margin, vertic_pos, data.preparations[0],
            fontName="Helvetica", fontSize=9))
        # measure prefix length to offset first line
        offset = rl_pdfmetrics.stringWidth(
            data.preparations[0], fontName="Helvetica", fontSize=9)
        for line in data.preparations[1:]:
            label.add(rl_shapes.String(
                horiz_margin + offset, vertic_pos, line,
                fontName="Helvetica-Bold", fontSize=9))
            offset = 0.0  # Only first line is offset at right of prefix
            vertic_pos -= 10
    # Line(s) 5
    if data.sides_clashes:
        # draw prefix
        label.add(rl_shapes.String(
            horiz_margin, vertic_pos, data.sides_clashes[0],
            fontName="Helvetica", fontSize=9))
        # measure prefix length to offset first line
        offset = rl_pdfmetrics.stringWidth(
            data.sides_clashes[0], fontName="Helvetica", fontSize=9)
        for line in data.sides_clashes[1:]:
            label.add(rl_shapes.String(
                horiz_margin + offset, vertic_pos, line,
                fontName="Helvetica-Bold", fontSize=9))
            offset = 0.0  # Only first line is offset at right of prefix
            vertic_pos -= 10
    # Line(s) 6
    if data.other_restrictions:
        for line in data.other_restrictions:
            label.add(rl_shapes.String(
                horiz_margin, vertic_pos, line,
                fontName="Helvetica", fontSize=9))
            vertic_pos -= 10
    # Line(s) 7
    if data.ingredients:
        for line in data.ingredients:
            label.add(rl_shapes.String(
                horiz_margin, vertic_pos, line,
                fontName="Helvetica", fontSize=8))
            vertic_pos -= 9


def kcr_make_labels(date, kitchen_list,
                    main_dish_name, main_dish_ingredients):
    """Generate Meal Labels sheets as a PDF file.

    Generate a label for each main dish serving to be delivered. The
    sheet format is "Avery 5162" 8,5 X 11 inches, 2 cols X 7 lines.

    Uses pylabels package - see https://github.com/bcbnz/pylabels
    and ReportLab

    Args:
        date : The delivery date of the meals.
        kitchen_list : A dictionary of KitchenItem objects (see
            order/models) which contain detailed information about
            all the meals that have to be prepared for the day and
            the client requirements and restrictions.
        main_dish_name : A string, the name of today's main dish.
        main_dish_ingredient : A string, the comma separated list
            of all the ingredients in today's main dish.

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
        corner_radius=1.5)

    sheet = labels.Sheet(specs, draw_label, border=False)

    meal_labels = []
    for kititm in kitchen_list.values():
        meal_label = MealLabel(*meal_label_fields[1::2])
        meal_label = meal_label._replace(
            route=kititm.routename.upper(),
            date="{}".format(date.strftime("%a, %b-%d")),
            main_dish_name=main_dish_name,
            name=kititm.lastname + ", " + kititm.firstname[0:2] + ".")
        if kititm.meal_size == SIZE_CHOICES_LARGE:
            meal_label = meal_label._replace(size=ugettext('LARGE'))
        if kititm.incompatible_ingredients:
            meal_label = meal_label._replace(
                main_dish_name='_______________________________________',
                dish_clashes=textwrap.wrap(
                    ugettext('Restrictions') + ' : {}'.format(
                        ' , '.join(kititm.incompatible_ingredients)),
                    width=65,
                    break_long_words=False, break_on_hyphens=False))
        elif not kititm.sides_clashes:
            meal_label = meal_label._replace(
                ingredients=textwrap.wrap(
                    ugettext('Ingredients') + ' : {}'.format(
                        main_dish_ingredients),
                    width=74,
                    break_long_words=False, break_on_hyphens=False))
        if kititm.preparation:
            prefix = ugettext('Preparation') + ' : '
            # wrap all text including prefix
            preparation_list = textwrap.wrap(
                prefix + ' , '.join(kititm.preparation),
                width=65,
                break_long_words=False,
                break_on_hyphens=False)
            # remove prefix from first line
            preparation_list[0] = preparation_list[0][len(prefix):]
            meal_label = meal_label._replace(
                preparations=[prefix] + preparation_list)
        if kititm.sides_clashes:
            prefix = ugettext('Sides clashes') + ' : '
            # wrap all text including prefix
            sides_clashes_list = textwrap.wrap(
                prefix + ' , '.join(kititm.sides_clashes),
                width=65,
                break_long_words=False,
                break_on_hyphens=False)
            # remove prefix from first line
            sides_clashes_list[0] = sides_clashes_list[0][len(prefix):]
            meal_label = meal_label._replace(
                sides_clashes=[prefix] + sides_clashes_list)
        other_restrictions = []
        if kititm.sides_clashes:
            other_restrictions.extend(
                sorted(list(set(kititm.avoid_ingredients) -
                            set(kititm.sides_clashes))))
            other_restrictions.extend(
                sorted(list(set(kititm.restricted_items) -
                            set(kititm.sides_clashes))))
        else:
            other_restrictions.extend(
                sorted(list(set(kititm.avoid_ingredients) -
                            set(kititm.incompatible_ingredients))))
            other_restrictions.extend(
                sorted(list(set(kititm.restricted_items) -
                            set(kititm.incompatible_ingredients))))
        if other_restrictions:
            meal_label = meal_label._replace(
                other_restrictions=textwrap.wrap(
                    ugettext('Other restrictions') + ' : {}'.format(
                        ' , '.join(other_restrictions)),
                    width=65,
                    break_long_words=False, break_on_hyphens=False))
        for j in range(1, kititm.meal_qty + 1):
            meal_labels.append(meal_label)

    # find max lengths of fields to sort on
    routew = 0
    namew = 0
    for label in meal_labels:
        routew = max(routew, len(label.route))
        namew = max(namew, len(label.name))
    # generate grouping and sorting key
    for j in range(len(meal_labels)):
        route = ''  # for groups 1, 2 and 3 : sort by name
        if meal_labels[j].dish_clashes:     # has dish restrictions
            group = 1
        elif meal_labels[j].sides_clashes:  # has sides restrictions
            group = 2
        elif meal_labels[j].preparations:   # has food preparations
            group = 3
        else:                               # regular meal
            group = 4
            route = meal_labels[j].route        # sort by route, name
        meal_labels[j] = meal_labels[j]._replace(
            sortkey='{grp:1}{rou:{rouw}}{nam:{namw}}'.format(
                grp=group,
                rou=route, rouw=routew,
                nam=meal_labels[j].name, namw=namew))
    # generate labels into PDF
    for label in sorted(meal_labels, key=lambda x: x.sortkey):
        sheet.add_label(label)

    if sheet.label_count > 0:
        sheet.save(settings.MEAL_LABELS_FILE)
    return sheet.label_count

# END Meal labels


# Delivery route sheet view, helper classes and functions.


class MealLabels(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = 'sous_chef.read'

    def get(self, request, **kwargs):
        try:
            f = open(settings.MEAL_LABELS_FILE, "rb")
        except Exception:
            raise Http404("File " + settings.MEAL_LABELS_FILE + " does not exist")
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = \
            'attachment; filename="labels{}.pdf"'. \
            format(datetime.date.today().strftime("%Y%m%d"))
        response.write(f.read())
        f.close()
        return response


class DeliveryRouteSheet(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = 'sous_chef.read'

    def get(self, request, **kwargs):
        today = timezone.datetime.today()
        delivery_history = get_object_or_404(
            DeliveryHistory,
            route__pk=kwargs['pk'],
            date=today
        )
        route_list = Order.get_delivery_list(today, delivery_history.route_id)
        route_list = sort_sequence_ids(
            route_list, delivery_history.client_id_sequence
        )
        summary_lines, detail_lines = drs_make_lines(route_list)
        return render(request, 'route_sheet.html',
                      {'route': delivery_history.route,
                       'summary_lines': summary_lines,
                       'detail_lines': detail_lines})


RouteSummaryLine = \
    collections.namedtuple(
        'RouteSummaryLine',
        ['component_group',
         'component_group_trans',
         'rqty',
         'lqty'])


def drs_make_lines(route_list):
    # generate all the lines for the delivery route sheet

    summary_lines = {}
    for k, item in route_list.items():
        for delivery_item in item.delivery_items:
            component_group = delivery_item.component_group
            if component_group:
                line = summary_lines.setdefault(
                    component_group,
                    RouteSummaryLine(
                        component_group,
                        # find the translated name of the component group
                        next(cg for cg in COMPONENT_GROUP_CHOICES
                             if cg[0] == component_group)[1],
                        rqty=0,
                        lqty=0))
                if (component_group == COMPONENT_GROUP_CHOICES_MAIN_DISH and
                        delivery_item.size == SIZE_CHOICES_LARGE):
                    summary_lines[component_group] = \
                        line._replace(lqty=line.lqty +
                                      delivery_item.total_quantity)
                elif component_group != '':
                    summary_lines[component_group] = \
                        line._replace(rqty=line.rqty +
                                      delivery_item.total_quantity)

    summary_lines_sorted = sorted(
        summary_lines.values(),
        key=component_group_sorting)
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
    nodes = [tsp.Node(None,
                      settings.DELIVERY_STARTING_POINT_LAT_LONG[0],
                      settings.DELIVERY_STARTING_POINT_LAT_LONG[1])]
    for waypoint in data:
        node = tsp.Node(waypoint['id'], float(waypoint['latitude']),
                        float(waypoint['longitude']))
        node_to_waypoint[node] = waypoint
        nodes.append(node)
    # Optimize waypoints by solving the Travelling Salesman Problem
    nodes = tsp.solve(nodes)
    # Guard against starting point which is not in node_to_waypoint
    return [node_to_waypoint[node] for
            node in nodes if node in node_to_waypoint]


class RefreshOrderView(
        LoginRequiredMixin, PermissionRequiredMixin, generic.View):
    permission_required = 'sous_chef.edit'

    def get(self, request):
        delivery_date = date.today()
        clients = Client.ongoing.all()
        orders = Order.objects.auto_create_orders(delivery_date, clients)
        LogEntry.objects.log_action(
            user_id=1, content_type_id=1,
            object_id="", object_repr="Generation of orders for " + str(
                datetime.datetime.now().strftime('%m %d %Y %H:%M')),
            action_flag=ADDITION,
        )
        orders.sort(key=lambda o: (
            o.client.route.pk if o.client.route is not None else -1,
            o.pk
        ))
        context = {'orders': orders}
        return render(request, 'partials/generated_orders.html', context)
