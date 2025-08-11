from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NoteManager(models.Manager):
    pass


class UnreadNoteManager(NoteManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_read=0)


class NotePriority(models.Model):
    name = models.CharField(max_length=150, verbose_name=_("Name"))

    class Meta:
        verbose_name_plural = _("Note priorities")
        ordering = ("name",)

    def __str__(self):
        return "%s" % self.name


class NoteCategory(models.Model):
    name = models.CharField(max_length=150, verbose_name=_("Name"))

    class Meta:
        verbose_name_plural = _("Note categories")
        ordering = ("name",)

    def __str__(self):
        return "%s" % self.name


class Note(models.Model):
    class Meta:
        verbose_name_plural = _("Notes")
        ordering = ("-date_modified", "note")

    note = models.TextField(verbose_name=_("Note"))

    author = models.ForeignKey(
        User, verbose_name=_("Author"), null=True, on_delete=models.SET_NULL
    )

    date_created = models.DateTimeField(
        verbose_name=_("Date Created"),
        default=timezone.now,
    )

    date_modified = models.DateTimeField(
        verbose_name=_("Date Modified"),
        default=timezone.now,
    )

    is_read = models.BooleanField(verbose_name=_("Is read"), default=False)

    client = models.ForeignKey(
        "member.Client",
        verbose_name=_("Client"),
        related_name="client_notes",
        on_delete=models.CASCADE,
    )

    priority = models.ForeignKey(
        NotePriority,
        verbose_name=_("Priority"),
        related_name="notes",
        null=True,
        on_delete=models.SET_NULL,
    )

    category = models.ForeignKey(
        NoteCategory,
        verbose_name=_("Category"),
        related_name="notes",
        null=True,
        on_delete=models.SET_NULL,
    )

    is_deleted = models.BooleanField(verbose_name=_("Is deleted"), default=False)

    objects = NoteManager()

    unread = UnreadNoteManager()

    def __str__(self):
        return self.note

    def mark_as_read(self):
        """Mark a note as read."""
        if not self.is_read:
            self.is_read = True
            self.save()

    def mark_as_unread(self):
        """Mark a note as unread."""
        if self.is_read:
            self.is_read = False
            self.save()

    def delete(self):
        """Mark a note as being deleted."""
        self.is_deleted = True
        self.save()
