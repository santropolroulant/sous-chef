# coding: utf-8

import collections

from django.contrib.auth.views import login
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Prefetch
from django.views.generic import TemplateView
from souschef.member.models import Client, Route, Client_option, DAYS_OF_WEEK
from souschef.order.models import Order
from datetime import datetime


class HomeView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'sous_chef.read'
    template_name = 'pages/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)

        today = datetime.today()
        active_clients = Client.active.all().count()
        pending_clients = Client.pending.all().count()
        birthday_clients = Client.birthday_contact.get_birthday_boys_and_girls()
        billable_orders = Order.objects.get_billable_orders(
            today.year, today.month
        ).count()
        billable_orders_year = Order.objects.filter(
            status='D',
            delivery_date__year=datetime.today().year).count()
        route_table = self.calculate_route_table()
        context['active_clients'] = active_clients
        context['pending_clients'] = pending_clients
        context['birthday'] = birthday_clients
        context['billable_orders_month'] = billable_orders
        context['billable_orders_year'] = billable_orders_year
        context['routes'] = route_table
        context['total_scheduled_by_day'] = self.calculate_total_scheduled_by_day(route_table)
        context['total_episodic_by_day'] = self.calculate_total_episodic_by_day(route_table)
        return context

    def calculate_route_table(self):
        routes = Route.objects.prefetch_related(Prefetch(
            'client_set',
            to_attr='selected_clients',
            queryset=Client.objects.filter(
                status__in=(Client.ACTIVE, Client.PAUSED, Client.PENDING)
            ).prefetch_related(Prefetch(
                'client_option_set',
                queryset=Client_option.objects.select_related(
                    'option', 'client'
                ).filter(
                    option__name='meals_schedule'
                ).only(
                    'value', 'option__name', 'client', 'client__route'
                )
            )).only(
                'route',
                'meal_default_week',
                'delivery_type'
            )
        )).order_by('name').only('name')

        route_table = []
        for route in routes:
            episodic_defaults = collections.defaultdict(int)
            schedules = collections.defaultdict(int)
            for client in route.selected_clients:
                # meals_schedule are only for ongoing clients
                meals_schedule = dict(client.meals_schedule)

                # For each day, if there's a schedule, count schedule.
                for day, _ in DAYS_OF_WEEK:
                    if day in meals_schedule:
                        schedules[day] += meals_schedule[day].get(
                            'main_dish') or 0

                if client.delivery_type == 'E':  # Episodic
                    meals_default = dict(client.meals_default)
                    for day, _ in DAYS_OF_WEEK:
                        episodic_defaults[day] += meals_default[day].get('main_dish') or 0

            route_table.append((route.name, episodic_defaults, schedules))
        return route_table

    def calculate_total_scheduled_by_day(self, route_table):
        total_scheduled_by_day = {}
        for day, _ in DAYS_OF_WEEK:
            total_scheduled_by_day[day] = 0
            for route_entry in route_table:
                total_scheduled_by_day[day] += route_entry[2][day]
        return total_scheduled_by_day

    def calculate_total_episodic_by_day(self, route_table):
        total_episodic_by_day = {}
        for day, _ in DAYS_OF_WEEK:
            total_episodic_by_day[day] = 0
            for route_entry in route_table:
                total_episodic_by_day[day] += route_entry[1][day]
        return total_episodic_by_day


def custom_login(request):
    if request.user.is_authenticated:
        # Redirect to home if already logged in.
        return HttpResponseRedirect(reverse_lazy("page:home"))
    else:
        return login(request)
