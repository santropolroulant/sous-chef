import datetime
import json
from io import BytesIO

from django.contrib.auth.models import User
from django.db.models import Q
from django.test import (
    RequestFactory,
    TestCase,
)
from django.urls import (
    reverse,
    reverse_lazy,
)
from django.utils import timezone as tz
from django.utils.translation import gettext, gettext_lazy
from pypdf import PdfReader

from souschef.meal.constants import COMPONENT_GROUP_CHOICES_SIDES
from souschef.meal.factories import (
    ComponentFactory,
    ComponentIngredientFactory,
    IncompatibilityFactory,
    IngredientFactory,
    RestrictedItemFactory,
)
from souschef.meal.models import (
    Component,
    Component_ingredient,
    Ingredient,
    Menu,
)
from souschef.member.factories import (
    AddressFactory,
    ClientFactory,
    DeliveryHistoryFactory,
    MemberFactory,
    RouteFactory,
)
from souschef.member.models import (
    DAYS_OF_WEEK,
    Client,
    Client_avoid_ingredient,
    DeliveryHistory,
    Member,
    Restriction,
    Route,
)
from souschef.order.models import Order
from souschef.sous_chef.tests import TestMixin as SousChefTestMixin

from .filters import KitchenCountOrderFilter


class KitchenCountReportTestCase(SousChefTestMixin, TestCase):
    # This data set includes 'Ground porc' clashing ingredient
    # This data set includes 'Tracy' client lastname
    #   and his side dish is 'compote'
    fixtures = ["sample_data"]

    def setUp(self):
        self.force_login()

    def test_clashing_ingredient(self):
        """An ingredient we know will clash must be in the page"""
        today = datetime.date.today()
        # create orders today
        clients = Client.active.all()
        Order.objects.auto_create_orders(today, clients)
        # main dish and its ingredients today
        main_dishes = Component.objects.filter(name="Ginger pork")
        main_dish = main_dishes[0]
        dish_ingredients = Component.get_recipe_ingredients(main_dish.id)
        for ing in dish_ingredients:
            ci = Component_ingredient(component=main_dish, ingredient=ing, date=today)
            ci.save()
        # Add extra ingredient so that more clashing clients will
        #  require two pages on the PDF kitchen count report
        extra = Ingredient.objects.get(name="Walnuts")
        ci = Component_ingredient(component=main_dish, ingredient=extra, date=today)
        ci.save()
        # add sides ingredient
        sides_component = Component.objects.get(
            component_group=COMPONENT_GROUP_CHOICES_SIDES
        )
        extra = Ingredient.objects.get(name="Cabbage")
        ci = Component_ingredient(
            component=sides_component, ingredient=extra, date=today
        )
        ci.save()
        # menu today
        Menu.create_menu_and_components(
            today,
            [
                "Ginger pork",
                "Green Salad",
                "Fruit Salad",
                "Day s Dessert",
                "Day s Diabetic Dessert",
                "Day s Pudding",
                "Day s Compote",
            ],
        )
        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {"delivery_date": datetime.date.today(), "download": "kitchen_count"},
        )
        self.assertEqual(response.status_code, 200)
        pdf_data = PdfReader(BytesIO(response.content))
        pdf_content = pdf_data.pages[0].extract_text()
        self.assertTrue("Ground porc" in pdf_content)

    def test_no_components(self):
        """No orders on this day therefore no documents to download."""
        menu_day = datetime.date(1999, 1, 1)
        Menu.create_menu_and_components(
            menu_day,
            [
                "Ginger pork",
                "Green Salad",
                "Fruit Salad",
                "Day s Dessert",
                "Day s Diabetic Dessert",
                "Day s Pudding",
                "Day s Compote",
            ],
        )
        # main dish and its ingredients today
        main_dishes = Component.objects.filter(name="Ginger pork")
        main_dish = main_dishes[0]
        dish_ingredients = Component.get_recipe_ingredients(main_dish.id)
        for ing in dish_ingredients:
            ci = Component_ingredient(
                component=main_dish, ingredient=ing, date=menu_day
            )
            ci.save()
        # add sides ingredient
        sides_component = Component.objects.get(
            component_group=COMPONENT_GROUP_CHOICES_SIDES
        )
        extra = Ingredient.objects.get(name="Cabbage")
        ci = Component_ingredient(
            component=sides_component, ingredient=extra, date=menu_day
        )
        ci.save()

        response = self.client.get(
            reverse("delivery:kitchen_count"),
            {"delivery_date": menu_day.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"No kitchen count report available" in response.content)

    def test_pdf_kitchen_count_and_labels_reports(self):
        # generate orders today
        today = datetime.date.today()
        clients = Client.active.all()
        Order.objects.auto_create_orders(today, clients)
        # main dish and its ingredients today
        main_dishes = Component.objects.filter(name="Ginger pork")
        main_dish = main_dishes[0]
        dish_ingredients = Component.get_recipe_ingredients(main_dish.id)
        for ing in dish_ingredients:
            ci = Component_ingredient(component=main_dish, ingredient=ing, date=today)
            ci.save()
        # Add sides ingredient
        sides_component = Component.objects.get(
            component_group=COMPONENT_GROUP_CHOICES_SIDES
        )
        # This ingredient is in the restrictions of some clients in the data
        sides_ingredient = Ingredient.objects.get(name="Brussel sprouts")
        ci = Component_ingredient(
            component=sides_component, ingredient=sides_ingredient, date=today
        )
        ci.save()
        # menu today
        Menu.create_menu_and_components(
            today,
            [
                "Ginger pork",
                "Green Salad",
                "Fruit Salad",
                "Day s Dessert",
                "Day s Diabetic Dessert",
                "Day s Pudding",
                "Day s Compote",
                "Days Sides",
            ],
        )

        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "download": "kitchen_count",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue("ReportLab" in repr(response.content))

        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {"delivery_date": datetime.date.today().isoformat(), "download": "labels"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue("ReportLab" in repr(response.content))

    def test_ingredients_not_defined_redirect(self):
        # generate orders
        today = datetime.date.today()
        clients = Client.active.all()
        created_orders = Order.objects.auto_create_orders(today, clients)
        self.assertTrue(created_orders)

        num_menu_comp_created = Menu.create_menu_and_components(
            today,
            [
                "Ginger pork",
                "Green Salad",
                "Fruit Salad",
                "Day s Dessert",
                "Day s Diabetic Dessert",
                "Day s Pudding",
                "Day s Compote",
            ],
        )
        self.assertEqual(num_menu_comp_created, 7)

        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": today.isoformat(),
            },
        )
        # Ingredients were not defined; kitchen count page will redirect to the
        # ingredients page.
        self.assertEqual(response.status_code, 302)


class ChooseDayMainDishIngredientsTestCase(SousChefTestMixin, TestCase):
    fixtures = ["sample_data"]

    @classmethod
    def setUpTestData(cls):
        # This data set includes 'Ginger pork' main dish
        # This data set includes 'Coq au vin' main dish
        # This data set includes 'Ground porc' main dish ingredient
        # This data set includes 'Pepper' available ingredient
        # create orders for today
        clients = Client.active.all()
        Order.objects.auto_create_orders(datetime.date.today(), clients)

    def setUp(self):
        self.force_login()

    def test_known_ingredients(self):
        """Two ingredients we know must be in the page"""
        response = self.client.get(
            reverse_lazy("delivery:meal"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertTrue(
            b"Ground porc" in response.content and b"Pepper" in response.content
        )

    def test_date_with_dish_next(self):
        """From ingredient choice go to Kitchen Count Report."""
        response = self.client.get(reverse_lazy("delivery:meal"))
        maindish = Component.objects.get(name="Ginger pork")
        cis = Component_ingredient.objects.filter(date=None, component=maindish)
        ing_ids = [ci.ingredient.id for ci in cis]
        req = {}
        req["_update"] = "Confirm all ingredients"
        req["maindish"] = str(maindish.id)
        req["ingredients"] = ing_ids
        req["sides_ingredients"] = [
            Ingredient.objects.filter(name="zucchini").first().id
        ]
        req["delivery_date"] = datetime.date.today().isoformat()
        response = self.client.post(reverse_lazy("delivery:meal"), req)
        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "download": "kitchen_count",
            },
        )
        self.assertEqual(response.status_code, 200)
        pdf_data = PdfReader(BytesIO(response.content))
        pdf_content = pdf_data.pages[0].extract_text()
        self.assertTrue("Ginger pork" in pdf_content)

    def test_remember_day_ingredients(self):
        """After Kitchen Count Report we remember chosen ingredients."""
        response = self.client.get(reverse_lazy("delivery:meal"))
        maindish = Component.objects.get(name="Ginger pork")
        cis = Component_ingredient.objects.filter(date=None, component=maindish)
        ing_ids = [ci.ingredient.id for ci in cis]
        req = {}
        req["_update"] = "Confirm all ingredients"
        req["maindish"] = str(maindish.id)
        req["ingredients"] = ing_ids
        req["sides_ingredients"] = [Ingredient.objects.filter(name="Onions").first().id]
        req["delivery_date"] = datetime.date.today().isoformat()
        response = self.client.post(reverse_lazy("delivery:meal"), req)
        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "download": "kitchen_count",
            },
        )
        self.assertEqual(response.status_code, 200)
        pdf_data = PdfReader(BytesIO(response.content))
        pdf_content = pdf_data.pages[0].extract_text()
        self.assertTrue("Ginger pork" in pdf_content)
        response = self.client.get(
            reverse_lazy("delivery:meal"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertTrue(b"Ginger pork" in response.content)

    def test_restore_dish_recipe(self):
        """Restore dish ingredients to those of recipe."""
        # dish : Ginger pork with added Pepper
        response = self.client.get(reverse_lazy("delivery:meal"))
        maindish = Component.objects.get(name="Ginger pork")
        cis = Component_ingredient.objects.filter(date=None, component=maindish)
        ing_ids = [ci.ingredient.id for ci in cis]
        # dish and added ingredient must be in kitchen count
        req = {}
        req["_update"] = "Confirm all ingredients"
        req["maindish"] = str(maindish.id)
        req["ingredients"] = ing_ids + [Ingredient.objects.get(name="Pepper").id]
        req["sides_ingredients"] = [Ingredient.objects.all().first().id]
        req["delivery_date"] = datetime.date.today().isoformat()
        response = self.client.post(reverse_lazy("delivery:meal"), req)
        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "download": "kitchen_count",
            },
        )
        self.assertEqual(response.status_code, 200)
        pdf_data = PdfReader(BytesIO(response.content))
        pdf_content = pdf_data.pages[0].extract_text()
        self.assertTrue("Ginger pork" in pdf_content)
        self.assertTrue("Pepper" in pdf_content)
        # restore recipe
        response = self.client.post(
            reverse_lazy("delivery:meal"),
            {
                "_restore": "Restore recipe",
                "delivery_date": datetime.date.today().isoformat(),
            },
        )
        # update ingredients
        req = {}
        req["_update"] = "Confirm all ingredients"
        req["maindish"] = str(maindish.id)
        req["ingredients"] = ing_ids
        req["sides_ingredients"] = [Ingredient.objects.all().first().id]
        req["delivery_date"] = datetime.date.today().isoformat()
        response = self.client.post(reverse_lazy("delivery:meal"), req)
        # check that we have Ginger pork with no Pepper in Kitchen count
        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "download": "kitchen_count",
            },
        )
        self.assertEqual(response.status_code, 200)
        pdf_data = PdfReader(BytesIO(response.content))
        pdf_content = pdf_data.pages[0].extract_text()
        self.assertTrue("Ginger pork" in pdf_content)
        self.assertTrue("Pepper" not in pdf_content)

    def test_change_main_dish(self):
        """Change dish then go directly to Kitchen Count Report."""
        maindish = Component.objects.get(name="Coq au vin")
        cis = Component_ingredient.objects.filter(date=None, component=maindish)
        ing_ids = [ci.ingredient.id for ci in cis]

        response = self.client.get(reverse_lazy("delivery:meal_id", args=[maindish.id]))
        req = {}
        req["_update"] = "Update ingredients"
        req["maindish"] = str(maindish.id)
        req["ingredients"] = ing_ids
        req["sides_ingredients"] = [Ingredient.objects.all().first().id]
        req["delivery_date"] = datetime.date.today().isoformat()
        response = self.client.post(reverse_lazy("delivery:meal"), req)
        response = self.client.get(
            reverse_lazy("delivery:kitchen_count"),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "download": "kitchen_count",
            },
        )
        self.assertEqual(response.status_code, 200)
        pdf_data = PdfReader(BytesIO(response.content))
        pdf_content = pdf_data.pages[0].extract_text()
        self.assertTrue("Coq au vin" in pdf_content)

    def test_post_invalid_form(self):
        """Invalid form."""
        response = self.client.get(reverse_lazy("delivery:meal"))
        req = {}
        req["_update"] = "Next: Print Kitchen Count"
        req["maindish"] = "wrong"
        req["delivery_date"] = datetime.date.today().isoformat()
        response = self.client.post(reverse_lazy("delivery:meal"), req)

        self.assertIn(
            gettext(
                "Select a valid choice. That choice is not one of "
                "the available choices."
            ).encode(response.charset),
            response.content,
        )

    def test_if_valid_no_red_sign(self):
        o = Order.objects.first()
        o.delivery_date = tz.now()
        o.save()
        response = self.client.get(reverse("delivery:order"))
        self.assertNotIn(b'<i class="warning sign red icon"></i>', response.content)
        response = self.client.post(
            reverse("delivery:refresh_orders"),
            {"generateOrderDate": datetime.date.today().isoformat()},
        )
        self.assertNotIn(b'<i class="warning sign red icon"></i>', response.content)

    def test_no_route_error(self):
        o = Order.objects.first()
        o.delivery_date = tz.now()
        o.save()
        c = o.client
        c.route = None
        c.save()
        response = self.client.get(
            reverse("delivery:order"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertIn(b'<i class="warning sign red icon"></i>', response.content)
        response = self.client.post(
            reverse("delivery:refresh_orders"),
            {"generateOrderDate": datetime.date.today().isoformat()},
        )
        self.assertIn(b'<i class="warning sign red icon"></i>', response.content)

    def test_not_geolocalized_error(self):
        o = Order.objects.first()
        o.delivery_date = tz.now()
        o.save()
        c = o.client
        c.member.address.latitude = None
        c.member.address.longitude = None
        c.member.address.save()
        response = self.client.get(
            reverse("delivery:order"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertIn(b'<i class="warning sign red icon"></i>', response.content)
        response = self.client.post(
            reverse("delivery:refresh_orders"),
            {"generateOrderDate": datetime.date.today().isoformat()},
        )
        self.assertIn(b'<i class="warning sign red icon"></i>', response.content)

    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:meal")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_read_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:meal")
        # Run
        response = self.client.get(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        self.assertEqual(response.status_code, 200)

    def test_disable_form_fields_for_users_that_do_not_have_edit_permission(
        self,
    ):  # noqa
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:meal")
        # Run
        response = self.client.get(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        for field in response.context["form"]:
            assert field.field.disabled

    def test_do_not_allow_users_that_do_not_have_edit_permission_to_post_data(
        self,
    ):  # noqa
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:meal")
        # Run
        response = self.client.post(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        self.assertEqual(response.status_code, 403)


class DeliveryRouteSheetTestCase(SousChefTestMixin, TestCase):
    # This data set includes 'Blondin' client lastname
    #   in 'Centre Sud' route
    # This data set includes 'Tracy' client lastname
    #   in 'Mile-End' route
    #   and his side dish is 'compote'
    fixtures = ["sample_data"]

    def setUp(self):
        # generate orders today
        self.today = datetime.date.today()
        clients = Client.active.all()
        Order.objects.auto_create_orders(self.today, clients)
        self.route_id = Route.objects.get(name="Centre Sud").id
        self.force_login()

    def test_query(self):
        """Sample route sheet query."""
        route_list = Order.get_delivery_list(self.today, self.route_id)
        self.assertTrue("Blondin" in repr(route_list))

    def test_extra_similar_sides(self):
        """Test cumulative quantities for similar side dishes."""
        # Add two separate extra compote order items for 'Tracy'
        member = Member.objects.filter(lastname="Tracy")[0]
        client = Client.objects.get(member=member.id)
        order = Order.objects.get(client=client.id, delivery_date=self.today)
        self.assertEqual(order.client.id, client.id)
        mile_end_id = Route.objects.get(name="Mile-End").id
        route_list = Order.get_delivery_list(self.today, mile_end_id)
        self.assertTrue("Tracy" in repr(route_list))

    def test_sheet(self):
        """Sample route sheet page."""
        client = Client.objects.filter(member__lastname="Blondin")[0]
        route = Route.objects.get(pk=self.route_id)
        DeliveryHistoryFactory(
            route=route, date=tz.datetime.today(), client_id_sequence=[client.id]
        )
        response = self.client.get(
            reverse_lazy("delivery:route_sheet", args=[self.route_id]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertTrue(b"Blondin" in response.content)

    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:route_sheet", args=[self.route_id])
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_read_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        DeliveryHistoryFactory(
            route=Route.objects.get(pk=self.route_id), date=tz.datetime.today()
        )
        url = reverse("delivery:route_sheet", args=[self.route_id])
        # Run
        response = self.client.get(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        self.assertEqual(response.status_code, 200)


class RedirectAnonymousUserTestCase(SousChefTestMixin, TestCase):
    fixtures = ["sample_data"]

    def test_anonymous_user_gets_redirect_to_login_page(self):
        check = self.assertRedirectsWithAllMethods
        check(reverse("delivery:order"))
        check(reverse("delivery:meal"))
        meal = Component.objects.first()
        meal_id = meal.id
        check(reverse("delivery:meal_id", kwargs={"id": meal_id}))
        check(reverse("delivery:routes"))
        check(reverse("delivery:kitchen_count"))
        check(reverse("delivery:route_sheet", kwargs={"pk": 1}))
        check(reverse("delivery:refresh_orders"))


class OrderlistViewTestCase(SousChefTestMixin, TestCase):
    fixtures = ["sample_data"]

    def setUp(self):
        super().setUp()
        self.force_login()

    def test_can_filter_orders_by_client_names(self):
        # Setup
        Order.objects.all().update(delivery_date=tz.now())
        url = reverse("delivery:order")
        # Run
        response = self.client.get(url, {"client_name": "john"})
        # Check
        self.assertEqual(
            set(response.context["orders"]),
            set(
                Order.objects.filter(
                    Q(client__member__firstname__icontains="john")
                    | Q(client__member__lastname__icontains="john")
                )
            ),
        )

    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:order")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_read_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:order")
        # Run
        response = self.client.get(url)
        # Check
        self.assertEqual(response.status_code, 200)


class KitchenCountOrderFilterTestCase(SousChefTestMixin, TestCase):
    fixtures = ["sample_data"]

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_can_filter_orders_by_client_names(self):
        # Setup
        queryset = Order.objects.all()
        request_1 = self.factory.get("/")
        request_2 = self.factory.get("/", {"client_name": "john doe"})
        # Run
        filterset_1 = KitchenCountOrderFilter(request_1.GET, queryset)
        filterset_2 = KitchenCountOrderFilter(request_2.GET, queryset)
        # Check
        self.assertEqual(filterset_1.qs.count(), queryset.count())
        self.assertTrue(filterset_2.qs.count())
        self.assertEqual(
            set(filterset_2.qs),
            set(
                Order.objects.filter(
                    Q(client__member__firstname__icontains="john")
                    | Q(client__member__firstname__icontains="doe")
                    | Q(client__member__lastname__icontains="john")
                    | Q(client__member__lastname__icontains="doe")
                )
            ),
        )


class RoutesInformationViewTestCase(SousChefTestMixin, TestCase):
    fixtures = ["sample_data"]

    def setUp(self):
        super().setUp()
        self.force_login()

    def test_can_embed_additional_route_sheet_information_when_printing(self):
        # Setup
        url = reverse("delivery:routes")
        # Run
        response_1 = self.client.get(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        response_2 = self.client.get(
            url,
            {"download": "yes", "delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        self.assertNotIn("routes_dict", response_1)
        self.assertIn("routes_dict", response_2)

    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:routes")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_read_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:routes")
        # Run
        response = self.client.get(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        self.assertEqual(response.status_code, 200)


class KitchenCountViewTestCase(SousChefTestMixin, TestCase):
    fixtures = ["sample_data"]

    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:kitchen_count")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_read_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:kitchen_count")

        # main dish and its ingredients today
        main_dishes = Component.objects.filter(name="Ginger pork")
        main_dish = main_dishes[0]
        dish_ingredients = Component.get_recipe_ingredients(main_dish.id)
        for ing in dish_ingredients:
            ci = Component_ingredient(
                component=main_dish, ingredient=ing, date=datetime.date.today()
            )
            ci.save()
        # Add sides ingredient
        sides_component = Component.objects.get(
            component_group=COMPONENT_GROUP_CHOICES_SIDES
        )
        sides_ingredient = Ingredient.objects.get(name="Brussel sprouts")
        ci = Component_ingredient(
            component=sides_component,
            ingredient=sides_ingredient,
            date=datetime.date.today(),
        )
        ci.save()

        # Run
        response = self.client.get(
            url,
            {"delivery_date": datetime.date.today().isoformat()},
        )
        # Check
        self.assertEqual(response.status_code, 200)


class RefreshOrderViewTestCase(SousChefTestMixin, TestCase):
    def test_redirects_users_who_do_not_have_edit_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:refresh_orders")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_edit_permission(self):
        # Setup
        user = User.objects.create_superuser(
            username="foo", email="foo@example.com", password="secure"
        )
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("delivery:refresh_orders")
        # Run
        response = self.client.post(
            url,
            {"generateOrderDate": datetime.date.today().isoformat()},
        )
        # Check
        self.assertEqual(response.status_code, 200)

    def test_refresh_create_only_if_scheduled_today(self):
        """
        Refs bug #734.
        If a client is ongoing but don't have scheduled delivery,
        then don't create his order.
        """
        meals_default = {}
        data = {
            "main_dish_{}_quantity": 2,
            "size_{}": "R",
            "dessert_{}_quantity": 0,
            "diabetic_dessert_{}_quantity": 0,
            "fruit_salad_{}_quantity": 1,
            "green_salad_{}_quantity": 1,
            "pudding_{}_quantity": 1,
            "compote_{}_quantity": 0,
        }
        for day, _ in DAYS_OF_WEEK:
            for key_tmpl, value in data.items():
                meals_default[key_tmpl.format(day)] = value

        ongoing_clients = ClientFactory.create_batch(
            10,
            status=Client.ACTIVE,
            delivery_type=Client.ONGOING_DELIVERY,
            meal_default_week=meals_default,
            route=RouteFactory(),
        )

        # The meal schedule should exclude today.
        schedule_delivery = []
        weekday = datetime.date.today().weekday()
        for i, t in enumerate(DAYS_OF_WEEK):
            if i != weekday:
                schedule_delivery.append(t[0])

        for c in ongoing_clients:
            c.set_simple_meals_schedule(schedule_delivery)

        self.force_login()
        url = reverse("delivery:refresh_orders")
        response = self.client.post(
            url, {"generateOrderDate": datetime.date.today().isoformat()}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Order.objects.all().count(), 0)  # No order should be created.


class ExcludeMisconfiguredClientsTestCase(SousChefTestMixin, TestCase):
    """
    Test 4 clients:
    - c_valid: correctly configured
               id==10, avoid veggie_10->chicken_10, avoid wine_10
    - c_nr:    misconfigured: route==None
               id==20, avoid veggie_20->chicken_20, avoid wine_20
    - c_ng:    misconfigured: not .isgeolocalized
               id==30, avoid veggie_30->chicken_30, avoid wine_30
    - c_nrng:  misconfigured: route==None and not .isgeolocalized
               id==40, avoid veggie_40->chicken_40, avoid wine_40

    Test meal = chicken_10 + wine_10 + chicken_20 + wine_20 + ...

    c_nr, c_ng and c_nrng should be excluded.
    """

    @classmethod
    def setUpTestData(cls):
        meal_default_week = {
            "main_dish_friday_quantity": 1,
            "main_dish_monday_quantity": 1,
            "main_dish_saturday_quantity": 1,
            "main_dish_sunday_quantity": 1,
            "main_dish_thursday_quantity": 1,
            "main_dish_tuesday_quantity": 1,
            "main_dish_wednesday_quantity": 1,
            "size_friday": "L",
            "size_monday": "L",
            "size_saturday": "L",
            "size_sunday": "L",
            "size_thursday": "L",
            "size_tuesday": "L",
            "size_wednesday": "L",
            "dessert_friday_quantity": 1,
            "dessert_monday_quantity": 1,
            "dessert_saturday_quantity": 1,
            "dessert_sunday_quantity": 1,
            "dessert_thursday_quantity": 1,
            "dessert_tuesday_quantity": 1,
            "dessert_wednesday_quantity": 1,
        }
        cls.route1 = RouteFactory()
        cls.route2 = RouteFactory()
        cls.c_valid = ClientFactory(
            pk=10,
            status=Client.ACTIVE,
            delivery_type=Client.ONGOING_DELIVERY,  # ongoing
            route=cls.route1,
            meal_default_week=meal_default_week,
            member=MemberFactory(
                firstname="Valid", lastname="Valid", address=AddressFactory()
            ),
        )
        cls.c_nr = ClientFactory(
            pk=20,
            status=Client.ACTIVE,
            delivery_type=Client.ONGOING_DELIVERY,  # ongoing
            route=None,
            meal_default_week=meal_default_week,
            member=MemberFactory(
                firstname="Nronly", lastname="Nronly", address=AddressFactory()
            ),
        )
        cls.c_ng = ClientFactory(
            pk=30,
            status=Client.ACTIVE,
            delivery_type=Client.ONGOING_DELIVERY,  # ongoing
            route=cls.route2,
            meal_default_week=meal_default_week,
            member=MemberFactory(
                firstname="Ngonly",
                lastname="Ngonly",
                address=AddressFactory(latitude=None),
            ),
        )
        cls.c_nrng = ClientFactory(
            pk=40,
            status=Client.ACTIVE,
            delivery_type=Client.ONGOING_DELIVERY,  # ongoing
            route=None,
            meal_default_week=meal_default_week,
            member=MemberFactory(
                firstname="Nrng",
                lastname="Nrng",
                address=AddressFactory(longitude=None),
            ),
        )

        cls.main_dish = ComponentFactory(name="coq au vin", component_group="main_dish")
        cls.sides = ComponentFactory(name="sides", component_group="sides")

        cls.ingred_chickens = []
        cls.ingred_wines = []
        for client in (cls.c_valid, cls.c_nr, cls.c_ng, cls.c_nrng):
            # Ensure that orders are created when refrshing orders.
            client.set_simple_meals_schedule(
                [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
            )

            # client-specific ingredient (for testing clashes)
            this_chicken = IngredientFactory(
                name=f"chicken_{client.id}", ingredient_group="meat"
            )
            this_wine = IngredientFactory(
                name=f"wine_{client.id}", ingredient_group="oils_and_sauces"
            )

            # add them to main_dish
            ComponentIngredientFactory(component=cls.main_dish, ingredient=this_chicken)
            ComponentIngredientFactory(component=cls.main_dish, ingredient=this_wine)

            # all special veggies, special winehaters
            this_incompatib = IncompatibilityFactory(
                restricted_item=RestrictedItemFactory(
                    name=f"veggie_{client.id}", restricted_item_group="meat"
                ),
                ingredient=this_chicken,
            )
            Restriction.objects.create(
                client=client, restricted_item=this_incompatib.restricted_item
            )
            Client_avoid_ingredient.objects.create(client=client, ingredient=this_wine)

            # keep track of these chickens and wines
            cls.ingred_chickens.append(this_chicken)
            cls.ingred_wines.append(this_wine)

    def setUp(self):
        self.force_login()

    def _refresh_orders(self):
        return self.client.post(
            reverse("delivery:refresh_orders"),
            {"generateOrderDate": datetime.date.today().isoformat()},
        )

    def _today_meal(self):
        return self.client.post(
            reverse("delivery:meal"),
            {
                "maindish": [str(self.main_dish.id)],
                "_update": ["Next: Print Kitchen Count"],
                "ingredients": map(
                    lambda ingred: str(ingred.id),
                    self.ingred_chickens + self.ingred_wines,
                ),
                "sides_ingredients": map(
                    lambda ingred: str(ingred.id), self.ingred_chickens
                ),
                "delivery_date": datetime.date.today().isoformat(),
            },
        )

    def test_step_1__review_orders(self):
        response = self.client.get(
            reverse("delivery:order"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(len(response.context["orders"]), 0)
        self.assertEqual(
            response.content.count(b'<i class="warning sign red icon"></i>'), 0
        )
        # refresh to create orders
        response = self._refresh_orders()
        self.assertEqual(len(response.context["orders"]), 4)
        self.assertEqual(
            response.content.count(b'<i class="warning sign red icon"></i>'), 3
        )

    def test_step_3__component_table(self):
        _ = self._refresh_orders()
        response = self._today_meal()
        self.assertRedirects(
            response,
            reverse("delivery:meal")
            + f"?delivery_date={datetime.date.today().isoformat()}",
        )
        response = self.client.get(
            reverse("delivery:kitchen_count"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        component_lines = response.context["component_lines"]
        main_dish_component_line = next(
            cl
            for cl in component_lines
            if cl.component_group == gettext_lazy("Main Dish")
        )
        self.assertEqual(main_dish_component_line.rqty, 0)
        # only c_valid
        self.assertEqual(main_dish_component_line.lqty, 1)

    def test_step_3__clashing_ingredients_restrictions_table(self):
        _ = self._refresh_orders()
        response = self._today_meal()
        self.assertRedirects(
            response,
            reverse("delivery:meal")
            + f"?delivery_date={datetime.date.today().isoformat()}",
        )
        response = self.client.get(
            reverse("delivery:kitchen_count"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        meal_lines = response.context["meal_lines"]

        # contains c_valid (10)
        ml_valid_clash = next(
            ml
            for ml in meal_lines
            if "chicken_10" in ml.ingr_clash and "wine_10" in ml.ingr_clash
        )
        self.assertEqual(ml_valid_clash.rqty, 0)
        self.assertEqual(ml_valid_clash.lqty, 1)
        ml_valid_restrict = next(ml for ml in meal_lines if "veggie_10" in ml.rest_item)
        self.assertIn("Valid", ml_valid_restrict.client)

        # doesn't contain c_nronly (20)
        self.assertRaises(
            StopIteration,
            lambda: next(
                ml
                for ml in meal_lines
                if "chicken_20" in ml.ingr_clash and "wine_20" in ml.ingr_clash
            ),
        )
        self.assertRaises(
            StopIteration,
            lambda: next(ml for ml in meal_lines if "veggie_20" in ml.rest_item),
        )

        # doesn't contain c_ngonly (30)
        self.assertRaises(
            StopIteration,
            lambda: next(
                ml
                for ml in meal_lines
                if "chicken_30" in ml.ingr_clash and "wine_30" in ml.ingr_clash
            ),
        )
        self.assertRaises(
            StopIteration,
            lambda: next(ml for ml in meal_lines if "veggie_30" in ml.rest_item),
        )

        # doesn't contain c_nrng (40)
        self.assertRaises(
            StopIteration,
            lambda: next(
                ml
                for ml in meal_lines
                if "chicken_40" in ml.ingr_clash and "wine_40" in ml.ingr_clash
            ),
        )
        self.assertRaises(
            StopIteration,
            lambda: next(ml for ml in meal_lines if "veggie_40" in ml.rest_item),
        )

        # TOTAL SPECIALS
        ml_last = meal_lines[-2]
        self.assertEqual(ml_last.ingr_clash, "TOTAL SPECIALS")
        self.assertEqual(ml_last.rqty, 0)
        self.assertEqual(ml_last.lqty, 1)

        # TOTAL SIDE CLASHES
        ml_last = meal_lines[-1]
        self.assertEqual(ml_last.ingr_clash, "TOTAL SIDE CLASHES")
        self.assertEqual(ml_last.rqty, 0)
        self.assertEqual(ml_last.lqty, 1)

    def test_step_3__labels(self):
        _ = self._refresh_orders()
        response = self._today_meal()
        self.assertRedirects(
            response,
            reverse("delivery:meal")
            + f"?delivery_date={datetime.date.today().isoformat()}",
        )
        response = self.client.get(
            reverse("delivery:kitchen_count"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.context["has_data"], True)

    def test_step_4__routes_before_organizing(self):
        """
        Should ignore route==None and non geolocalized clients.
        When the delivery history doesn't exist or it's invalid,
        don't let route sheet and route sheets work.
        """
        _ = self._refresh_orders()
        _ = self._today_meal()
        response = self.client.get(
            reverse("delivery:routes"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        route_orders_tuples = response.context["route_details"]
        route_orders_dict = dict(map(lambda t: (t[0], t[1:]), route_orders_tuples))
        self.assertIn(self.route1, route_orders_dict)
        self.assertEqual(route_orders_dict[self.route1][0], 1)
        self.assertIn(self.route2, route_orders_dict)
        self.assertEqual(route_orders_dict[self.route2][0], 0)
        # Assert not configured
        self.assertFalse(response.context["all_configured"])
        self.assertFalse(
            DeliveryHistory.objects.filter(
                route=self.route1, date=tz.datetime.today()
            ).exists()
        )
        self.assertFalse(
            DeliveryHistory.objects.filter(
                route=self.route2, date=tz.datetime.today()
            ).exists()
        )
        # Assert print doesn't work
        response = self.client.get(
            reverse("delivery:routes"),
            {"download": "yes", "delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)
        # Assert route sheets don't exist
        response = self.client.get(
            reverse("delivery:route_sheet", args=[self.route1.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            reverse("delivery:route_sheet", args=[self.route2.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)

        # Try invalid DeliveryHistory
        DeliveryHistory.objects.create(
            route=self.route1,
            date=tz.datetime.today(),
            # As long as this sequence is not exactly same as the clients',
            # it's always invalid, even if it contains all the clients.
            client_id_sequence=[999999, 888888, self.c_valid.pk],
        )
        # Assert print doesn't work
        response = self.client.get(
            reverse("delivery:routes"),
            {"download": "yes", "delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)

    def test_step_4__routes_after_organizing(self):
        """
        Should ignore route==None and not geolocalized
        """
        _ = self._refresh_orders()
        _ = self._today_meal()
        # Work on Route 1
        response = self.client.post(
            reverse("delivery:create_delivery", args=[self.route1.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertRedirects(
            response,
            reverse("delivery:edit_delivery_route", args=[self.route1.pk])
            + f"?delivery_date={datetime.date.today().isoformat()}",
        )
        self.assertTrue(
            DeliveryHistory.objects.filter(
                route=self.route1, date=tz.datetime.today()
            ).exists()
        )
        response = self.client.get(
            reverse("delivery:edit_delivery_route", args=[self.route1.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("delivery:edit_delivery_route", args=[self.route1.pk]),
            {
                "delivery_date": datetime.date.today().isoformat(),
                "vehicle": "walking",
                "comments": "My bicycle is broken",
                "client_id_sequence": json.dumps([self.c_valid.pk]),
            },
        )
        self.assertRedirects(
            response,
            reverse("delivery:routes")
            + f"?delivery_date={datetime.date.today().isoformat()}",
        )

        # Assert configured because Route 2 is empty.
        response = self.client.get(
            reverse("delivery:routes"),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertTrue(response.context["all_configured"])

        # Assert Route 2 doesn't allow the creation of delivery
        response = self.client.post(
            reverse("delivery:create_delivery", args=[self.route2.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            DeliveryHistory.objects.filter(
                route=self.route2, date=tz.datetime.today()
            ).exists()
        )
        response = self.client.get(
            reverse("delivery:edit_delivery_route", args=[self.route2.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse("delivery:edit_delivery_route", args=[self.route2.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response.status_code, 404)

        # Assert print works
        response = self.client.get(
            reverse("delivery:routes"),
            {"delivery_date": datetime.date.today().isoformat(), "download": "yes"},
        )
        self.assertEqual(response.status_code, 200)
        # Check print result
        routes_dict = json.loads(response["routes_dict"])
        # only route1 has one client
        route1 = routes_dict[str(self.route1.id)]
        self.assertEqual(len(route1["detail_lines"]), 1)
        # route2 doesn't exist.
        self.assertNotIn(str(self.route2.id), routes_dict)

        # check output page : use data in header because cannot read PDF
        route_name_list = [item["route"] for item in routes_dict.values()]
        self.assertIn(self.route1.name, route_name_list)
        self.assertNotIn(self.route2.name, route_name_list)

        # Assert route sheets exist and check route sheets
        # Route 1
        response1 = self.client.get(
            reverse("delivery:route_sheet", args=[self.route1.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response1.status_code, 200)
        # 1 dessert 1 L main_dish
        summary_line1 = response1.context["summary_lines"]
        main_dish_line1 = next(
            ln for ln in summary_line1 if ln.component_group == "main_dish"
        )
        self.assertEqual(main_dish_line1.rqty, 0)
        self.assertEqual(main_dish_line1.lqty, 1)
        dessert_line1 = next(
            ln for ln in summary_line1 if ln.component_group == "dessert"
        )
        self.assertEqual(dessert_line1.rqty, 1)
        # 1 client
        detail_line1 = response1.context["detail_lines"]
        self.assertEqual(len(detail_line1), 1)
        self.assertEqual(detail_line1[0].firstname, "Valid")
        self.assertEqual(detail_line1[0].lastname, "Valid")

        # Route 2 - not found
        response2 = self.client.get(
            reverse("delivery:route_sheet", args=[self.route2.pk]),
            {"delivery_date": datetime.date.today().isoformat()},
        )
        self.assertEqual(response2.status_code, 404)


class RouteSheetReportTestCase(SousChefTestMixin, TestCase):
    # PDF route sheets report generation
    fixtures = ["sample_data"]

    def setUp(self):
        self.force_login()

    def test_route_sheet_report(self):
        # generate orders today
        Order.objects.auto_create_orders(datetime.date.today(), Client.active.all())

        # list all the routes
        response = self.client.get(
            reverse("delivery:routes"), {"delivery_date": datetime.date.today()}
        )
        self.assertEqual(response.status_code, 200)
        # get details of each route : {route:(order_count, ...), ...}
        route_orders_dict = dict(
            map(lambda t: (t[0], t[1:]), response.context["route_details"])
        )

        # create history and organize clients for the non empty routes
        for route, num in route_orders_dict.items():
            if num[0] > 0:
                # route has clients with orders : create delivery history
                response = self.client.post(
                    reverse("delivery:create_delivery", args=[route.pk]),
                    {"delivery_date": datetime.date.today().isoformat()},
                )
                self.assertRedirects(
                    response,
                    reverse("delivery:edit_delivery_route", args=[route.pk])
                    + f"?delivery_date={datetime.date.today().isoformat()}",
                )

                # get the clients in the route
                response = self.client.get(
                    reverse("delivery:edit_delivery_route", args=[route.pk]),
                    {"delivery_date": datetime.date.today()},
                )
                self.assertEqual(response.status_code, 200)
                client_pks = [
                    item.pk for item in response.context["clients_on_delivery_history"]
                ]

                # organize the clients in the route
                response = self.client.post(
                    reverse("delivery:edit_delivery_route", args=[route.pk]),
                    {
                        "vehicle": "walking",
                        "comments": "Nice day !",
                        "client_id_sequence": json.dumps(client_pks),
                        "delivery_date": datetime.date.today().isoformat(),
                    },
                )
                self.assertRedirects(
                    response,
                    reverse("delivery:routes")
                    + f"?delivery_date={datetime.date.today().isoformat()}",
                )

        # generate the PDF route sheets of all the routes
        response = self.client.get(
            reverse("delivery:routes"),
            {
                "download": "yes",
                "delivery_date": datetime.date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue("ReportLab" in repr(response.content))
