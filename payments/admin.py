from django.contrib import admin
from django.utils import timezone
# Register your models here.
from django.contrib import admin
from .models import Seller, Transaction, PhoneNumber, Status
from django.db import models, transaction
from .models import CreditRequest


# payments/admin.py
from django.contrib import admin
from .models import Seller, Transaction, PhoneNumber, CreditRequest, Status

# Register Seller and Transaction
admin.site.register(Seller)
admin.site.register(Transaction)

@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display  = ['id', 'number', 'name', 'balance', 'created_at']
    search_fields = ['number', 'name']

@admin.register(CreditRequest)
class CreditRequestAdmin(admin.ModelAdmin):
    list_display    = ['id', 'seller', 'amount', 'status_label', 'created_at', 'approved_at']
    list_filter     = ['status', 'processed', 'created_at', 'approved_at']
    readonly_fields = ['created_at', 'approved_at']
    exclude         = ['processed']       # hide the internal flag from the form
    actions         = ['approve_requests', 'reject_requests', 'set_pending']

    def status_label(self, obj):
        return Status(obj.status).label
    status_label.short_description = 'Status'

    @admin.action(description="Approve selected credit requests")
    def approve_requests(self, request, queryset):
        for cr in queryset:
            cr.status = Status.APPROVED
            cr.save()  # model.save() handles the first-ever bump
        self.message_user(request, f"{queryset.count()} request(s) set to Approved.")

    @admin.action(description="Reject selected credit requests")
    def reject_requests(self, request, queryset):
        # Mark rejected and processed so no future bump
        count = queryset.update(status=Status.REJECTED, processed=True)
        self.message_user(request, f"{count} request(s) set to Rejected.")

    @admin.action(description="Set selected credit requests to Pending")
    def set_pending(self, request, queryset):
        # Bring back to pending; processed remains True if they were rejected before
        count = queryset.update(status=Status.PENDING)
        self.message_user(request, f"{count} request(s) set to Pending.")