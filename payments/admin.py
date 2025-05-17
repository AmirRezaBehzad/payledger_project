from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Seller, Transaction

admin.site.register(Seller)
admin.site.register(Transaction)