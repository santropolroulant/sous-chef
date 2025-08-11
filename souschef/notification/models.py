from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Meta:
        verbose_name_plural = _("notifications")

    description = models.TextField(verbose_name=_("description"))

    member = models.ForeignKey(
        "member.Member", verbose_name=_("member"), on_delete=models.CASCADE
    )

    date = models.DateField(auto_now=False, auto_now_add=False, default=timezone.now)

    def __str__(self):
        return self.description
