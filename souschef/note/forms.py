from django import forms

from souschef.member.models import Client
from souschef.note.models import Note


class NoteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)
        self.fields["client"].queryset = (
            Client.objects.all()
            .select_related("member")
            .only("member__firstname", "member__lastname")
        )

    class Meta:
        model = Note
        fields = ["note", "client", "priority", "category"]

        widgets = {
            "note": forms.Textarea(attrs={"rows": 7}),
            "client": forms.Select(attrs={"class": "ui search dropdown"}),
            "priority": forms.Select(attrs={"class": "ui dropdown"}),
            "category": forms.Select(attrs={"class": "ui dropdown"}),
        }


class NoteEditForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["note", "priority", "category"]

        widgets = {
            "note": forms.Textarea(attrs={"rows": 7}),
            "priority": forms.Select(attrs={"class": "ui dropdown"}),
            "category": forms.Select(attrs={"class": "ui dropdown"}),
        }
