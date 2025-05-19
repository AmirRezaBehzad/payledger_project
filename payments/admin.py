from django.contrib import admin
from django.utils import timezone
# Register your models here.
from django.contrib import admin
from .models import Seller, Transaction, PhoneNumber, Status
from django.db import models, transaction
from .models import CreditRequest


admin.site.register(Seller)
admin.site.register(Transaction)

@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'name', 'balance', 'created_at']  # نمایش balance در لیست ادمین
    search_fields = ['number', 'name']  # جستجو با شماره و نام شماره

@admin.register(CreditRequest)
class CreditRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'seller', 'amount', 'status_label', 'created_at', 'approved_at']
    list_filter = ['status', 'created_at', 'approved_at']  # Filter by the name of the related status model
    readonly_fields = ['created_at', 'approved_at']
    actions = ['approve_requests', 'reject_requests', 'set_pending']

    def status_label(self, obj):
        return Status(obj.status).label
    status_label.short_description = 'Status'

    def approve_requests(self, request, queryset):
        # Only pending requests
        to_approve = queryset.filter(status=Status.PENDING)
        for cr in to_approve:
            cr.status = Status.APPROVED
            cr.approved_at = timezone.now()
            cr.save()
            # bump seller balance
            seller = cr.seller
            seller.balance += cr.amount
            seller.save()
            # log transaction
            Transaction.objects.create(
                seller=seller,
                amount=cr.amount,
                transaction_type='credit',
                description=f"Admin-approved CreditRequest #{cr.id}"
            )
        self.message_user(request, "Selected requests approved and balances updated.")
    approve_requests.short_description = "Approve selected credit requests"

    def reject_requests(self, request, queryset):
        # Only pending requests
        queryset.filter(status=Status.PENDING).update(status=Status.REJECTED)
        self.message_user(request, "Selected requests marked as rejected.")
    reject_requests.short_description = "Reject selected credit requests"

    def set_pending(self, request, queryset):
        # Reset any non-pending to pending
        queryset.exclude(status=Status.PENDING).update(status=Status.PENDING)
        self.message_user(request, "Selected requests set to pending.")
    set_pending.short_description = "Set selected credit requests to pending"