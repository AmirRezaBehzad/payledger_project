from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class Seller(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Seller {self.username or self.phone_number} - Balance: {self.balance}"