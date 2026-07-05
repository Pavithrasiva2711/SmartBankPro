from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin configuration for Customer model.
    """

    list_display = (
        "account_number",
        "full_name",
        "email",
        "mobile",
        "account_type",
        "balance",
        "is_active",
    )

    search_fields = (
        "full_name",
        "email",
        "account_number",
    )

    list_filter = (
        "account_type",
        "is_active",
    )