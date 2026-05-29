from django.contrib import admin

from souschef.note.models import (
    Note,
    NoteCategory,
    NotePriority,
)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        "date_created",
        "date_modified",
        "author",
        "is_read",
        "is_deleted",
        "priority",
        "category",
        "client",
        "note",
    )
    list_filter = (
        "priority",
        "category",
        "is_read",
        "is_deleted",
    )


# Register your models here.
admin.site.register((NotePriority, NoteCategory))
