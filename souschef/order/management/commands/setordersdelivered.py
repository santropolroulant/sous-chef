from datetime import datetime

from django.contrib.admin.models import (
    ADDITION,
    LogEntry,
)
from django.core.management.base import BaseCommand

from souschef.order.constants import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_ORDERED,
)
from souschef.order.models import (
    Order,
)


class Command(BaseCommand):
    help = "Set status to Delivered for all orders that have the status\
            Ordered for the specified delivery date."

    def add_arguments(self, parser):
        parser.add_argument(
            "delivery_date",
            help="The date must be in the format YYYY-MM-DD",
        )

    def handle(self, *args, **options):
        delivery_date = datetime.strptime(options["delivery_date"], "%Y-%m-%d").date()

        numorders = Order.objects.filter(
            status=ORDER_STATUS_ORDERED, delivery_date=delivery_date
        ).update(status=ORDER_STATUS_DELIVERED)

        # Log the execution
        LogEntry.objects.log_action(
            user_id=1,
            content_type_id=1,
            object_id="",
            object_repr="Status set to delivered for orders on"
            + str(delivery_date.strftime("%Y-%m-%d %H:%M")),
            action_flag=ADDITION,
        )
        print(
            f"Status set to Delivered for {numorders} orders whose "
            f"delivery date is {delivery_date}."
        )
