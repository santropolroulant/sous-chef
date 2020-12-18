import json

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse

from souschef.member.factories import RouteFactory, ClientFactory
from souschef.member.models import Client, Option, Client_option


class HomeViewTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='test'
        )

    def test_access_as_admin(self):
        """Only logged-in users can access the homepage"""
        self.client.login(
            username=self.admin.username,
            password="test"
        )
        result = self.client.get(
            reverse_lazy(
                'page:home'
            ),
            follow=False
        )
        self.assertEqual(result.status_code, 200)

    def test_as_anonymous(self):
        """User not logged-in can not access the homepage"""
        self.client.logout()
        result = self.client.get(
            reverse_lazy(
                'page:home'
            ),
            follow=True
        )
        self.assertRedirects(
            result,
            reverse('page:login') + '?next=/p/home',
            status_code=302
        )

    def test_route_meal_statistics(self):
        """
        On dashboard, routes statistics should display:
        "scheduled dishes (+ episodic default dishes)"
        for active, paused and pending clients.
        """
        self.client.login(
            username=self.admin.username,
            password="test"
        )

        route_factory1 = RouteFactory()
        route_factory2 = RouteFactory()
        route_factory_empty = RouteFactory()  # Empty route

        meals_schedule_option, _ = Option.objects.get_or_create(
            name='meals_schedule', option_group='dish'
        )

        test_clients = (
            # Status        Deliv  Route Mon T Wed T Fri S Sun
            (Client.PENDING, 'E', route_factory1, 0, 2, 3, 4, 5, 6, 7),  # 1
            (Client.PENDING, 'E', route_factory2, 2, 3, 0, 1, 0, 3, 5),  # 2
            (Client.PENDING, 'E', route_factory2, 2, 0, 0, 1, 2, 3, 5),  # 3
            (Client.ACTIVE,  'E', route_factory1, 1, 2, 3, 4, 5, 6, 0),  # 4
            (Client.ACTIVE,  'E', route_factory1, 1, 0, 3, 0, 5, 6, 3),  # 5
            (Client.ACTIVE,  'E', route_factory2, 2, 3, 4, 1, 2, 3, 1),  # 6
            (Client.PAUSED,  'E', route_factory1, 1, 2, 3, 4, 0, 4, 3),  # 7
            (Client.PAUSED,  'E', route_factory2, 2, 3, 0, 1, 2, 3, 5),  # 8
            (Client.PAUSED,  'E', route_factory2, 2, 3, 4, 0, 2, 3, 5),  # 9
            (Client.STOPNOCONTACT, 'E', route_factory1, 1, 2, 0, 4, 5, 6, 3),  # 10
            (Client.STOPNOCONTACT, 'E', route_factory2, 0, 3, 4, 1, 2, 3, 1),  # 11
            (Client.STOPCONTACT,   'E', route_factory1, 1, 2, 3, 4, 5, 6, 7),  # 12
            (Client.STOPCONTACT,   'E', route_factory1, 1, 0, 3, 4, 5, 6, 7),  # 13
            (Client.STOPCONTACT,   'E', route_factory2, 2, 3, 4, 1, 2, 3, 5),  # 14
            (Client.DECEASED,  'E', route_factory1, 1, 2, 0, 4, 5, 6, 3),  # 15
            (Client.DECEASED,  'E', route_factory2, 2, 3, 4, 1, 0, 3, 1),  # 16

            (Client.PENDING, 'O', route_factory1, 1, 2, 3, 4, 5, 6, 7),  # 51
            (Client.PENDING, 'O', route_factory1, 7, 6, 5, 4, 3, 2, 1),  # 52
            (Client.PENDING, 'O', route_factory2, 2, 0, 4, 1, 2, 3, 5),  # 53
            (Client.ACTIVE,  'O', route_factory1, 6, 5, 0, 3, 2, 1, 5),  # 54
            (Client.ACTIVE,  'O', route_factory2, 2, 3, 0, 1, 0, 3, 1),  # 55
            (Client.ACTIVE,  'O', route_factory2, 2, 0, 4, 1, 2, 3, 1),  # 56
            (Client.PAUSED,  'O', route_factory1, 1, 2, 0, 4, 0, 4, 3),  # 57
            (Client.PAUSED,  'O', route_factory1, 1, 0, 3, 4, 2, 4, 3),  # 58
            (Client.PAUSED,  'O', route_factory2, 0, 3, 0, 1, 0, 3, 5),  # 59
            (Client.STOPNOCONTACT, 'O', route_factory1, 1, 2, 3, 4, 5, 6, 3),  # 60
            (Client.STOPNOCONTACT, 'O', route_factory2, 2, 3, 4, 1, 2, 3, 1),  # 61
            (Client.STOPCONTACT,   'O', route_factory1, 1, 2, 3, 4, 5, 6, 7),  # 62
            (Client.STOPCONTACT,   'O', route_factory1, 1, 0, 3, 4, 5, 6, 7),  # 63
            (Client.STOPCONTACT,   'O', route_factory2, 2, 3, 4, 1, 2, 3, 5),  # 64
            (Client.DECEASED,  'O', route_factory1, 1, 2, 3, 4, 5, 6, 3),  # 65
            (Client.DECEASED,  'O', route_factory2, 2, 3, 4, 1, 2, 3, 1),  # 66
        )

        for status, delivery_type, route_factory, mon, tue, wed, thu, fri, sat, sun in test_clients:
            client_factory = ClientFactory(
                status=status,
                delivery_type=delivery_type,
                route=route_factory,
                meal_default_week={
                    "main_dish_monday_quantity": mon,
                    "main_dish_tuesday_quantity": tue,
                    "main_dish_wednesday_quantity": wed,
                    "main_dish_thursday_quantity": thu,
                    "main_dish_friday_quantity": fri,
                    "main_dish_saturday_quantity": sat,
                    "main_dish_sunday_quantity": sun,
                    "size_monday": "R",
                    "size_tuesday": "L",
                    "size_wednesday": "R",
                    "size_thursday": "R",
                    "size_friday": "R",
                    "size_saturday": "R",
                    "size_sunday": "R",
                    # These fields really doesn't matter
                    "diabetic_monday_quantity": 666,
                    "fruit_salad_monday_quantity": 666,
                    "compote_tuesday_quantity": 666,
                    "dessert_wednesday_quantity": 666,
                    "diabetic_thursday_quantity": 666,
                    "fruit_salad_thursday_quantity": 666,
                    "diabetic_friday_quantity": 666,
                    "fruit_salad_friday_quantity": 666,
                    "compote_saturday_quantity": 666,
                    "dessert_saturday_quantity": 666,
                    "diabetic_sunday_quantity": 666,
                    "fruit_salad_sunday_quantity": 666
                }
            )

            if delivery_type == 'O':
                # Ongoing: only two delivery days!
                Client_option.objects.create(
                    client=client_factory,
                    option=meals_schedule_option,
                    value=json.dumps(['tuesday', 'wednesday'])
                )

        response = self.client.get(
            reverse_lazy(
                'page:home'
            ),
            follow=False
        )
        self.assertEqual(response.status_code, 200)
        routes = response.context['routes']
        routes = {route_name: (schedules, defaults)
                  for route_name, defaults, schedules in routes}

        self.assertIn(route_factory1.name, routes)
        self.assertIn(route_factory2.name, routes)
        self.assertIn(route_factory_empty.name, routes)

        route1 = routes[route_factory1.name]
        route2 = routes[route_factory2.name]
        route_empty = routes[route_factory_empty.name]

        # Ongoing dishes -- ongoing clients on delivery days
        # Test clients 51 & 52 & 54 & 57 & 58
        self.assertEqual(route1[0].get('monday', 0), 0)
        self.assertEqual(route1[0].get('tuesday', 0), 2 + 6 + 5 + 2 + 0)
        self.assertEqual(route1[0].get('wednesday', 0), 3 + 5 + 0 + 0 + 3)
        self.assertEqual(route1[0].get('thursday', 0), 0)
        self.assertEqual(route1[0].get('friday', 0), 0)
        self.assertEqual(route1[0].get('saturday', 0), 0)
        self.assertEqual(route1[0].get('sunday', 0), 0)

        # Test clients 53 & 55 & 56 & 59
        self.assertEqual(route2[0].get('monday', 0), 0)
        self.assertEqual(route2[0].get('tuesday', 0), 0 + 3 + 0 + 3)
        self.assertEqual(route2[0].get('wednesday', 0), 4 + 0 + 4 + 0)
        self.assertEqual(route2[0].get('thursday', 0), 0)
        self.assertEqual(route2[0].get('friday', 0), 0)
        self.assertEqual(route2[0].get('saturday', 0), 0)
        self.assertEqual(route2[0].get('sunday', 0), 0)

        self.assertEqual(route_empty[0].get('monday', 0), 0)
        self.assertEqual(route_empty[0].get('tuesday', 0), 0)
        self.assertEqual(route_empty[0].get('wednesday', 0), 0)
        self.assertEqual(route_empty[0].get('thursday', 0), 0)
        self.assertEqual(route_empty[0].get('friday', 0), 0)
        self.assertEqual(route_empty[0].get('saturday', 0), 0)
        self.assertEqual(route_empty[0].get('sunday', 0), 0)

        # Episodic dishes -- ongoing clients out of delivery days
        #                    and episodic clients
        # Test clients 1 & 4 & 5 & 7 (episodic)
        #              51 & 52 & 54 & 57 & 58 (ongoing)
        self.assertEqual(route1[1].get('monday', 0), 3)
        self.assertEqual(route1[1].get('tuesday', 0), 6)
        self.assertEqual(route1[1].get('wednesday', 0), 12)
        self.assertEqual(route1[1].get('thursday', 0), 12)
        self.assertEqual(route1[1].get('friday', 0), 15)
        self.assertEqual(route1[1].get('saturday', 0), 22)
        self.assertEqual(route1[1].get('sunday', 0), 13)

        # Test clients 2 & 3 & 6 & 8 & 9 (episodic)
        #              53 & 55 & 56 & 59 (ongoing)
        self.assertEqual(route2[1].get('monday', 0), 10)
        self.assertEqual(route2[1].get('tuesday', 0), 12)
        self.assertEqual(route2[1].get('wednesday', 0), 8)
        self.assertEqual(route2[1].get('thursday', 0), 4)
        self.assertEqual(route2[1].get('friday', 0), 8)
        self.assertEqual(route2[1].get('saturday', 0), 15)
        self.assertEqual(route2[1].get('sunday', 0), 21)

        self.assertEqual(route_empty[1].get('monday', 0), 0)
        self.assertEqual(route_empty[1].get('tuesday', 0), 0)
        self.assertEqual(route_empty[1].get('wednesday', 0), 0)
        self.assertEqual(route_empty[1].get('thursday', 0), 0)
        self.assertEqual(route_empty[1].get('friday', 0), 0)
        self.assertEqual(route_empty[1].get('saturday', 0), 0)
        self.assertEqual(route_empty[1].get('sunday', 0), 0)
