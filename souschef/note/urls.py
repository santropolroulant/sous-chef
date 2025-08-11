from django.urls import path

from souschef.note.views import (
    NoteAdd,
    NoteBatchToggle,
    NoteDeleteView,
    NoteEditView,
    NoteList,
    mark_as_read,
    mark_as_unread,
)

app_name = "note"

urlpatterns = [
    path("", NoteList.as_view(), name="note_list"),
    path("read/<int:id>/", mark_as_read, name="read"),
    path("unread/<int:id>/", mark_as_unread, name="unread"),
    path("add/", NoteAdd.as_view(), name="note_add"),
    path("batch_toggle/", NoteBatchToggle.as_view(), name="batch_toggle"),
    path("edit/<int:pk>/", NoteEditView.as_view(), name="edit"),
    path(
        "delete/<int:pk>/",
        NoteDeleteView.as_view(),
        name="note_delete",
    ),
]
