import csv
from datetime import date

from django.core.management.base import BaseCommand
from django.core.management import call_command

from souschef.meal.models import Ingredient, Restricted_item
from souschef.member.models import Client, Member, Route


class Command(BaseCommand):
    help = 'Export an empty template for new categorization of kitchen count.'

    headers = [
        'ingredient_id',
        'ingredient_name',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            required=True,
            help='The output path you want to use',
        )

    def handle(self, *args, **options):
        self.stdout.write('Generating new template...')

        with open(options['output'], 'w') as csvfile:
            # Restricted_item is a categorization system allowing to
            # group ingredient into subset of restriction we can re-use
            # for multiple Client
            categories = Restricted_item.objects.all()

            writer = csv.writer(csvfile)
            writer.writerow(self._get_headers(categories))

            for ingredient in Ingredient.objects.all():
                ingredient_row = [
                    str(ingredient.id),
                    ingredient.name,
                ]

                for category in categories:
                    if category.ingredients.filter(id=ingredient.id).exists():
                        ingredient_row.append('x')
                    else:
                        ingredient_row.append('')

                writer.writerow(ingredient_row)

        self.stdout.write('New template generated!')

    def _get_headers(self, categories):
        """
        Headers depends on all the categories already in the system
        Args:
            categories: A list of Restricted_item we want to take in account

        Returns: A list where each string is a column header of the CSV

        """
        headers = self.headers
        for category in Restricted_item.objects.all():
            headers.append(category.name)

        return headers
