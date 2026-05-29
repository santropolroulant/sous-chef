from django.contrib import admin

from souschef.billing.models import Billing


# Register your models here.
class OrdersInline(admin.TabularInline):
    model = Billing.orders.through


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    inlines = [
        OrdersInline,
    ]


