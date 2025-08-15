import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from souschef.billing.factories import BillingFactory
from souschef.billing.models import (
    Billing,
    calculate_amount_total,
)
from souschef.member.constants import RATE_TYPE_DEFAULT, RATE_TYPE_LOW_INCOME
from souschef.member.factories import ClientFactory
from souschef.member.models import Client
from souschef.order.constants import ORDER_STATUS_DELIVERED
from souschef.order.factories import OrderFactory
from souschef.order.models import Order
from souschef.sous_chef.tests import TestMixin as SousChefTestMixin

AMOUNT_COL = "Montant"
CLASS_COL = "Classe"
CUSTOMER_COL = "Client"
DESCRIPTION_COL = "Description"
DUE_DATE_COL = "Échéance"
INVOICE_DATE_COL = "Date de facturation"
INVOICE_NO_COL = "Nº de facture"
PRODUCT_COL = "Produit/service"
QUANTITY_COL = "Qté"
RATE_COL = "Taux"
TERMS_COL = "Modalités"


class BillingTestCase(TestCase):
    fixtures = ["routes.json"]

    @classmethod
    def setUpTestData(cls):
        cls.client1 = ClientFactory()
        cls.billed_orders = OrderFactory.create_batch(
            10,
            delivery_date=datetime.today(),
            client=cls.client1,
            status="D",
        )
        cls.orders = OrderFactory.create_batch(
            10,
            delivery_date=datetime.today(),
            client=ClientFactory(),
            status="O",
        )

    def test_get_billable_orders(self):
        """
        Test that all the delivered orders for a given month are fetched.
        """
        month = datetime.now().strftime("%m")
        year = datetime.now().strftime("%Y")
        orders = Order.objects.get_billable_orders(year, month)
        self.assertEqual(len(self.billed_orders), orders.count())

    def testTotalAmount(self):
        total_amount = calculate_amount_total(self.orders)
        self.assertEqual(total_amount, 50)

    def testOrderDetail(self):
        pass

    def test_get_billable_orders_client(self):
        """
        Test that all the delivered orders for a given month and
        a given client are fetched.
        """
        month = datetime.now().strftime("%m")
        year = datetime.now().strftime("%Y")
        orders = Order.objects.get_billable_orders_client(month, year, self.client1)
        self.assertEqual(len(self.billed_orders), orders.count())


class BillingManagerTestCase(TestCase):
    fixtures = ["routes.json"]

    def setUp(self):
        self.today = datetime.today()
        self.billable_orders = OrderFactory.create_batch(
            10,
            delivery_date=self.today,
            status="D",
        )

    def test_billing_create_new(self):
        billing = Billing.objects.billing_create_new(self.today.year, self.today.month)
        self.assertEqual(10, billing.orders.all().count())
        self.assertEqual(self.today.month, billing.billing_month)
        self.assertEqual(self.today.year, billing.billing_year)
        # We created 10 orders, with one billable 10$ value item each
        self.assertEqual(50.00, billing.total_amount)

    def test_billing_get_period(self):
        billing = Billing.objects.billing_get_period(self.today.year, self.today.month)
        self.assertEqual(None, billing)


class RedirectAnonymousUserTestCase(SousChefTestMixin, TestCase):
    fixtures = ["routes.json"]

    def test_anonymous_user_gets_redirect_to_login_page(self):
        check = self.assertRedirectsWithAllMethods
        check(reverse("billing:list"))
        check(reverse("billing:create"))
        check(reverse("billing:add"))
        bill = BillingFactory()
        check(reverse("billing:view", kwargs={"pk": bill.id}))
        check(reverse("billing:delete", kwargs={"pk": bill.id}))


class BillingListViewTestCase(SousChefTestMixin, TestCase):
    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        url = reverse("billing:list")
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
        url = reverse("billing:list")
        # Run
        response = self.client.get(url)
        # Check
        self.assertEqual(response.status_code, 200)


class BillingCreateViewTestCase(SousChefTestMixin, TestCase):
    def test_redirects_users_who_do_not_have_edit_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("billing:create")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_edit_permission(self):
        # Setup
        user = User.objects.create_superuser(
            username="foo", email="foo@example.com", password="secure"
        )
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("billing:create")
        # Run
        response = self.client.get(url, {"delivery_date": ""}, follow=True)
        # Check
        self.assertEqual(response.status_code, 200)
        self.assertTrue("error message" in repr(response.content))
        response = self.client.get(url, {"delivery_date": "2016-1"}, follow=True)
        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], reverse("billing:list"))


class BillingAddViewTestCase(SousChefTestMixin, TestCase):
    def test_redirects_users_who_do_not_have_edit_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("billing:add")
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_edit_permission(self):
        # Setup
        user = User.objects.create_superuser(
            username="foo", email="foo@example.com", password="secure"
        )
        user.save()
        self.client.login(username="foo", password="secure")
        url = reverse("billing:add")
        # Run
        response = self.client.get(url)
        # Check
        self.assertEqual(response.status_code, 200)


class BillingSummaryViewTestCase(SousChefTestMixin, TestCase):
    fixtures = ["routes.json"]

    def test_redirects_users_who_do_not_have_read_permission(self):
        # Setup
        User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        self.client.login(username="foo", password="secure")
        bill = BillingFactory()
        url = reverse("billing:view", args=(bill.id,))
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
        bill = BillingFactory()
        url = reverse("billing:view", args=(bill.id,))
        # Run
        response = self.client.get(url)
        # Check
        self.assertEqual(response.status_code, 200)

    def test_csv_export(self):
        EXPECTED_ORDER_TOTAL = 105

        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")

        # Will create orders to cover all pricing cases:
        # - clients with default and low income rates
        # - orders with regular and large meals, and with extras
        billing = BillingFactory(
            total_amount=0,
            billing_year=2025,
            billing_month=8,
        )
        default_rate_client = ClientFactory(
            rate_type=RATE_TYPE_DEFAULT, status=Client.ACTIVE
        )
        low_income_client = ClientFactory(
            rate_type=RATE_TYPE_LOW_INCOME, status=Client.ACTIVE
        )
        orders = []
        for client in (default_rate_client, low_income_client):
            for meal_size in ("R", "L"):
                for is_main_dish_billable in (True, False):
                    # qty 2 = same as number of meal = non-billable
                    # qty 4 = 1 extra per meal = billable
                    for dessert_quantity in (2, 4):
                        order = Order.objects.create_order(
                            delivery_date=date(2025, 8, 14),
                            client=client,
                            items={
                                "main_dish_default_quantity": 2,
                                "size_default": meal_size,
                                "dessert_default_quantity": dessert_quantity,
                                "diabetic_default_quantity": 0,
                                "fruit_salad_default_quantity": 0,
                                "green_salad_default_quantity": 0,
                                "pudding_default_quantity": 0,
                                "compote_default_quantity": 0,
                                "delivery_default": True,
                            },
                            is_main_dish_billable=is_main_dish_billable,
                        )
                        order.status = ORDER_STATUS_DELIVERED
                        billing.orders.add(order)
                        orders.append(order)

        billing.total_amount = sum(order.price for order in orders)
        self.assertEqual(EXPECTED_ORDER_TOTAL, billing.total_amount)

        url = reverse("billing:view", args=(billing.id,))
        # Run
        response = self.client.get(url, {"format": "csv"})
        # Check
        self.assertEqual(response.status_code, 200)

        rows = list(csv.DictReader(StringIO(response.content.decode())))
        self.assertEqual(10, len(rows))

        firstrow = rows[0]
        self.assertTrue(int(firstrow[INVOICE_NO_COL]))
        self.assertTrue(firstrow[CUSTOMER_COL])
        self.assertTrue(firstrow[DESCRIPTION_COL])
        self.assertEqual("2025-08-31", firstrow[INVOICE_DATE_COL])
        self.assertEqual("2025-08-31", firstrow[DUE_DATE_COL])
        self.assertEqual("Payable dès réception", firstrow[TERMS_COL])

        csv_total = Decimal(0)
        for row in rows:
            self.assertEqual("2 - Béatrice:Popote - Clients", row[CLASS_COL])
            self.assertTrue(Decimal(row[QUANTITY_COL]) > 0)
            self.assertTrue(Decimal(row[RATE_COL]) >= 0)
            self.assertEqual(
                Decimal(row[AMOUNT_COL]),
                Decimal(row[QUANTITY_COL]) * Decimal(row[RATE_COL]),
            )
            csv_total += Decimal(row[AMOUNT_COL])

        items = [(row[QUANTITY_COL], row[PRODUCT_COL], row[AMOUNT_COL]) for row in rows]
        self.assertEqual(
            sorted(items),
            [
                ("4", "Popote roulante", "24.00"),
                ("4", "Popote roulante_Large_non-chargé", "0"),
                ("4", "Popote roulante_Large_non-chargé", "0"),
                ("4", "Popote roulante_Low income", "18.00"),
                ("4", "Popote roulante_Low income Large", "21.00"),
                ("4", "Popote roulante_Repas Large", "28.00"),
                ("4", "Popote roulante_non-chargé", "0"),
                ("4", "Popote roulante_non-chargé", "0"),
                ("8", "Popote roulante_Extra", "8.00"),
                ("8", "Popote roulante_Extra Low Income", "6.00"),
            ],
        )

        self.assertEqual(Decimal(EXPECTED_ORDER_TOTAL), csv_total)


class BillingDeleteViewTestCase(SousChefTestMixin, TestCase):
    def test_redirects_users_who_do_not_have_edit_permission(self):
        # Setup
        user = User.objects.create_user(
            username="foo", email="foo@example.com", password="secure"
        )
        user.is_staff = True
        user.save()
        self.client.login(username="foo", password="secure")
        bill = BillingFactory()
        url = reverse("billing:delete", args=(bill.id,))
        # Run & check
        self.assertRedirectsWithAllMethods(url)

    def test_allow_access_to_users_with_edit_permission(self):
        # Setup
        user = User.objects.create_superuser(
            username="foo", email="foo@example.com", password="secure"
        )
        user.save()
        self.client.login(username="foo", password="secure")
        bill = BillingFactory()
        url = reverse("billing:delete", args=(bill.id,))
        # Run
        response = self.client.post(url, {"next": "/"}, follow=True)
        # Check
        self.assertEqual(response.status_code, 200)
