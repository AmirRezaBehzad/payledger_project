from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Seller

@admin.register(Seller)
class SellerAdmin(UserAdmin):
    list_display = ['id', 'username', 'phone_number', 'balance', 'is_active', 'is_superuser']
    list_filter = ['is_active', 'is_superuser', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_superuser=False)