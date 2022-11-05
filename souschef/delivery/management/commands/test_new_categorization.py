import csv
import itertools
import time
from django.core.management.base import BaseCommand
from souschef.member.models import Client


class Command(BaseCommand):
    help = 'Test kitchen count with new categorization.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            required=True,
            help='The categorization file to use',
        )

    def handle(self, *args, **options):
        with open(options['file'], mode='r') as file:
            reader = csv.reader(file)

            count = 0
            for line in reader:
                count += 1

                if count == 1:
                    categories = self._extract_categories_from_headers(line)

                else:
                    categories = self._add_ingredient_into_categories(
                        categories,
                        line,
                    )

        self.stdout.write(
            'Analyzed the {0} new categories!'.format(len(categories))
        )

        clients = self._define_clients_new_categories(categories)

        self._security_check(clients)

        self.stdout.write(
            self.style.ERROR(
                'This command is not finished implementing yet.'
            )
        )

    def _extract_categories_from_headers(self, headers):
        """
        Extract the new categories names from the CSV header line

        Args:
            headers: a list of string representing the header line of the csv

        Returns: A list of categories definition
        """

        categories_name = headers[2:]

        self.stdout.write(
            'Found {0} categories to import...'.format(len(categories_name))
        )

        categories = []

        for category_name in categories_name:
            categories.append(
                {
                    'name': category_name,
                    'ingredients': list(),
                }
            )

        return categories

    def _add_ingredient_into_categories(self, categories, csvLine):
        """
        Add ingredient into the categories definitions
        Args:
            categories: A list of categories definition
            csvLine: An ingredient line from the CSV

        Returns: A list of categories definition updated with new ingredient
        """

        ingredient_id = csvLine[0]

        # We init the cursor on the 2nd cell
        # the first containing cross for categories inclusion
        cursor = 1
        for category in categories:
            cursor += 1
            if csvLine[cursor] != '':
                category['ingredients'].append(ingredient_id)

        return categories

    def _define_clients_new_categories(self, new_categories):
        """
        Define with new categories every client should have based on the
        old categorization system

        Args:
            new_categories: A list of categories definition with ingredients

        Returns:
        """
        clients = []

        self._generate_combinations_of_new_categorization(new_categories)

        self.stdout.write(
            'Found {0} clients to refresh...'.format(
                Client.objects.all().count(),
            )
        )

        for client in Client.objects.all():
            ingredients = self._get_actual_ingredient_restriction(client)
            categories = self._define_client_new_categorization(
                ingredients,
            )

            clients.append(
                {
                    'id': client.id,
                    'ingredients': ingredients,
                    'categories': categories,
                }
            )

        return clients

    def _get_actual_ingredient_restriction(self, client):
        """
        Analyze a specific client and return its list of restricted ingredient.

        Args:
            client: The client we want to analyze

        Returns: The list of ingredient restriction that the client have
        """

        restrictions = client.restrictions.all()

        restricted_ingredients = []
        for restriction in restrictions:
            new_ingredient = [r.id for r in restriction.ingredients.all()]
            restricted_ingredients += new_ingredient

        restricted_ingredients = set(restricted_ingredients)

        return restricted_ingredients

    def _generate_combinations_of_new_categorization(self, categories):
        start = time.time()

        combinations = []
        for length in range(len(categories)):
            combinations += list(
                itertools.combinations(categories, length + 1)
            )

        self.categories_combinations = combinations

        end = time.time()

        diff = round(end - start, 5)

        self.stdout.write(
            'Generated the {0} combinations of categorization '
            'in {1} seconds...'.format(
                len(combinations),
                diff,
            )
        )

        return True

    def _define_client_new_categorization(self, ingredients):
        """
        Define which categorization would be the best fit for a client with
        a defined list of restricted ingredient.

        Args:
            ingredients: The list of restricted ingredient
=
        Returns: A list of new category we should set on the client
        """

        index = -1

        # Compare all combination and keep valid one
        valid_combinations = []

        for combination in self.categories_combinations:
            index += 1

            # get list of restrictions inside the combination
            restrictions = []
            for category in combination:
                restrictions += category['ingredients']

            restrictions = set(restrictions)

            # check if combination is valid
            if set(ingredients).issubset(restrictions):
                valid_combinations.append(
                    {
                        'index': index,
                        'nb_restrictions': len(restrictions),
                    }
                )

        # Define the best combination in the valid ones
        best_combination = None
        if len(valid_combinations):
            for combination in valid_combinations:
                # Default choice
                if best_combination is None:
                    best_combination = combination

                if combination['nb_restrictions'] < best_combination['nb_restrictions']:
                    best_combination = combination

        return best_combination

    def _security_check(self, clients):
        """
        This function print some statistics and ask the user if we can
        proceed with the import

        Args:
            clients: A list of clients

        Returns: None
        """
        # Check number of client incompatible with new categorization system
        incompatible_clients = []

        for client in clients:
            if client['categories'] is None:
                incompatible_clients.append(client)

        if len(incompatible_clients):
            self.stdout.write(
                self.style.WARNING(
                    '{0} clients are incompatible with the new '
                    'categorization system'.format(
                        len(incompatible_clients),
                    )
                )
            )

        # Check average number of restriction added
        number_of_added_restriction = []
        for client in clients:
            if client['categories'] is not None:
                initial_restriction = client['ingredients']
                new_restriction = client['categories']['nb_restrictions']
                diff = new_restriction - len(initial_restriction)
                number_of_added_restriction.append(diff)

        if len(number_of_added_restriction):
            average = sum(number_of_added_restriction) / \
                      len(number_of_added_restriction)
            self.stdout.write(
                self.style.WARNING(
                    '{0} restrictions will be added on each '
                    'client in average'.format(
                        average,
                    )
                )
            )
