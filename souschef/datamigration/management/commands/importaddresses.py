import csv

from django.core.management.base import BaseCommand
from souschef.member.models import Member, Address, Contact, EMAIL, HOME


class Command(BaseCommand):
    help = 'Data: import clients from given csv file.'

    ROW_MID = 0
    ROW_ADDRESS1 = 3
    ROW_APARTMENT = 4
    ROW_CITY = 5
    ROW_POSTAL_CODE = 6
    ROW_PHONE = 7
    ROW_EMAIL = 8

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=False,
            help='Import mock data instead of actual data',
        )

    def handle(self, *args, **options):
        if options['file']:
            file = 'mock_addresses.csv'
        else:
            file = 'clients_address.csv'

        with open(file) as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                try:
                    member = Member.objects.get(mid=row[self.ROW_MID])
                    # if member.address is not None:
                    #    member.address.delete()
                    address = Address.objects.create(
                        street=row[self.ROW_ADDRESS1],
                        apartment=row[self.ROW_APARTMENT],
                        city=row[self.ROW_CITY],
                        postal_code=row[self.ROW_POSTAL_CODE],
                    )

                    member.address = address
                    member.save()

                    contacts = Contact.objects.filter(member=member)
                    contacts.delete()

                    if row[self.ROW_PHONE] != '':
                        Contact.objects.create(
                            type=HOME,
                            value=row[self.ROW_PHONE],
                            member=member
                        )
                    if row[self.ROW_EMAIL] != '':
                        Contact.objects.create(
                            type=EMAIL,
                            value=row[self.ROW_EMAIL],
                            member=member
                        )

                except Member.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING('Non existing member'))
