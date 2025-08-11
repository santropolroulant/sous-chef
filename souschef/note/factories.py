import random

import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory

from souschef.member.factories import ClientFactory
from souschef.note.models import (
    Note,
    NoteCategory,
    NotePriority,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.LazyAttribute(lambda obj: "%s@example.com" % obj.username)


class NoteFactory(DjangoModelFactory):
    class Meta:
        model = Note

    note = factory.Faker("sentence")
    author = factory.SubFactory(UserFactory)

    client = factory.SubFactory(ClientFactory)
    priority = factory.LazyAttribute(
        lambda x: random.choice(NotePriority.objects.all())
    )
    category = factory.LazyAttribute(
        lambda x: random.choice(NoteCategory.objects.all())
    )
