from datetime import (
    datetime,
    timedelta,
)

from django.contrib.admin.models import (
    ADDITION,
    LogEntry,
)
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from souschef.member.models import Client
from souschef.order.models import Order


class Command(BaseCommand):
    help = "Create new orders for a given delivery date for all\
            ongoing active clients using their meals defaults."

    def add_arguments(self, parser):
        parser.add_argument(
            "delivery_date",
            help="The date must be in the format YYYY-MM-DD",
        )
        parser.add_argument(
            "--days",
            help=(
                "The number of days to be created in advance."
                "There will not be duplicates."
            ),
            default=1,
            type=int,
        )

    def handle(self, *args, **options):
        start_date = datetime.strptime(options["delivery_date"], "%Y-%m-%d").date()
        days = options["days"]

        # Only active ongoing clients can receive orders
        clients = Client.ongoing.all()

        for i in range(days):
            # Create the orders
            delivery_date = start_date + timedelta(days=i)
            orders = Order.objects.auto_create_orders(delivery_date, clients)
            # Log the execution
            LogEntry.objects.log_action(
                user_id=1,
                content_type_id=1,
                object_id="",
                object_repr="Orders creation for "
                + str(delivery_date.strftime("%Y-%m-%d %H:%M")),
                action_flag=ADDITION,
            )
            print(
                _("{} orders created on {}: to be delivered on {}.").format(
                    len(orders), start_date, delivery_date
                )
            )
