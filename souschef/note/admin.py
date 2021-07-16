from django.contrib import admin
from souschef.note.models import Note, NotePriority, NoteCategory

class NoteAdmin(admin.ModelAdmin):
   list_filter = ('priority', 'category', 'is_read', 'is_deleted')


# Register your models here.
admin.site.register(Note, NoteAdmin)
admin.site.register((NotePriority, NoteCategory))
