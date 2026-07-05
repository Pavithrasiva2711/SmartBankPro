from django.db import models
from django.contrib.auth.models import User
import uuid


class Customer(models.Model):
    """
    Stores customer banking information.
    Authentication is handled by Django's built-in User model.
    """

    ACCOUNT_CHOICES = [
        ("Savings", "Savings"),
        ("Current", "Current"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer"
    )

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    address = models.TextField()

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_CHOICES,
        default="Savings"
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )

    account_number = models.CharField(
        max_length=15,
        unique=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.account_number})"


class Transaction(models.Model):

    TRANSACTION_TYPES = [
        ("Deposit", "Deposit"),
        ("Withdraw", "Withdraw"),
        ("Transfer", "Transfer"),
        ("Received", "Received"),
    ]

    STATUS_CHOICES = [
        ("Success", "Success"),
        ("Failed", "Failed"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    receiver_account = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    reference_number = models.CharField(
        max_length=25,
        unique=True,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Success"
    )

    remarks = models.CharField(
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = "TXN" + uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_number} - {self.transaction_type}"