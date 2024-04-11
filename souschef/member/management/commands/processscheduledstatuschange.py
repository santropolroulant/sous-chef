from datetime import (
    date,
    datetime,
)

from django.core.management.base import BaseCommand

from souschef.member.models import ClientScheduledStatus


class Command(BaseCommand):
    help = "Process scheduled status changes, \
        queued in «member_ClientScheduledStatus» table."

    def handle(self, *args, **options):
        # List all change not processed, and older or equal to now
        changes = ClientScheduledStatus.objects.filter(
            operation_status=ClientScheduledStatus.TOBEPROCESSED
        ).filter(change_date__lte=date.today())

        # For each change to be processed,
        for scheduled_change in changes:
            if scheduled_change.process():
                suc_msg = (
                    f": client «{scheduled_change.client.member}» status updated "
                    f"from {scheduled_change.get_status_from_display()} to "
                    f"{scheduled_change.get_status_to_display()}."
                )
                self.stdout.write(self.style.SUCCESS(str(datetime.now()) + suc_msg))
            # If not, mark change as processed with error
            else:
                err_msg = (
                    f": client «{scheduled_change.client.member}» status not updated."
                )
                err_msg += (
                    " Current status is "
                    f"«{scheduled_change.client.get_status_display()}», should be "
                    f"«{scheduled_change.get_status_from_display()}»."
                )
                self.stdout.write(self.style.ERROR(str(datetime.now()) + err_msg))
