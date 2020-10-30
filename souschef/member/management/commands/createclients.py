from django.core.management.base import BaseCommand
from souschef.member.factories import ClientFactory
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Creates a happy bunch of clients without orders'

    def handle(self, *args, **options):
        # Load fixtures for the routes
        fixture_filename = 'routes.json'
        call_command('loaddata', fixture_filename)

        client = ClientFactory.create_batch(10)
        self.stdout.write(
            self.style.SUCCESS(
                'Successfully created client "%s"' % client
            )
        )
