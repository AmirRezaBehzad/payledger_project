from django.db import models

# Create your models here.
from django.db import models

class Seller(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Seller {self.phone_number} - Balance: {self.balance}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),  # افزایش اعتبار
        ('debit', 'Debit'),    # فروش شارژ (کاهش اعتبار)
    ]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.transaction_type} {self.amount} for {self.seller.phone_number} at {self.timestamp}"


