import csv

from django.core.management.base import BaseCommand

from souschef.member.models import (
    Client,
    Member,
)
from souschef.order.models import Order


class Command(BaseCommand):
    help = "Data: import clients relationships from given csv file."

    ROW_MID = 0
    ROW_DATE = 1
    ROW_STATUS = 2
    ROW_MAIN_DISH_QUANTITY = 3
    ROW_SIZE = 4
    ROW_FRUIT_SALAD = 5
    ROW_GREEN_SALAD = 6
    ROW_DIABETIC_DESSERT = 7
    ROW_DESSERT = 8
    ROW_PUDDING = 9

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=False,
            help="Import mock data instead of actual data",
        )

    def handle(self, *args, **options):
        file = "mock_orders.csv" if options["file"] else "clients_orders.csv"

        with open(file) as f:
            reader = csv.reader(f, delimiter=";")
            for row in reader:
                try:
                    member = Member.objects.get(mid=row[self.ROW_MID])
                    client = Client.objects.get(member=member)
                    delivery_date = row[self.ROW_DATE]
                    items = {
                        "main_dish_default_quantity": int(
                            row[self.ROW_MAIN_DISH_QUANTITY]
                        ),
                        "dessert_default_quantity": int(row[self.ROW_DESSERT]),
                        "diabetic_default_quantity": int(
                            row[self.ROW_DIABETIC_DESSERT]
                        ),
                        "fruit_salad_default_quantity": int(row[self.ROW_FRUIT_SALAD]),
                        "green_salad_default_quantity": int(row[self.ROW_GREEN_SALAD]),
                        "pudding_default_quantity": int(row[self.ROW_PUDDING]),
                        "compote_default_quantity": 0,
                        "size_default": row[self.ROW_SIZE],
                    }

                    order = Order.objects.create_order(delivery_date, client, items)

                    order.status = row[self.ROW_STATUS]
                    order.save()

                except Member.DoesNotExist:
                    self.stdout.write(self.style.WARNING("Non existing member"))
                except Client.DoesNotExist:
                    self.stdout.write(self.style.WARNING("Non existing client"))
