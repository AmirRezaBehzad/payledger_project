from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import CreditRequest, PhoneCharge, Transaction, PhoneNumber, Status

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'seller_info', 'phone_info', 'amount', 'transaction_type', 'timestamp']
    list_filter = ['transaction_type', 'timestamp']
    search_fields = ['seller__username', 'description']
    ordering = ['-timestamp']

    def seller_info(self, obj):
        return f"{obj.seller.username} - Balance: {obj.seller.balance}"
    seller_info.short_description = 'Seller'

    def phone_info(self, obj):
        if obj.transaction_type == 'debit':
            phone_charge = PhoneCharge.objects.filter(
                seller=obj.seller,
                amount=obj.amount
            ).order_by('-created_at').first()
            if phone_charge:
                phone = phone_charge.phone_number
                return f"{phone.number} - Balance: {phone.balance}"
            else:
                return "N/A"
        else:
            return "-"
    phone_info.short_description = 'Phone Number'


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display  = ['id', 'number', 'name', 'balance', 'created_at']
    search_fields = ['number', 'name']


@admin.register(CreditRequest)
class CreditRequestAdmin(admin.ModelAdmin):
    list_display        = ['id', 'seller', 'amount', 'status', 'created_at', 'processed_at']
    # list_display        = ['id', 'seller', 'amount', 'status_label', 'created_at', 'processed_at']
    list_filter         = ['status', 'created_at', 'processed_at']
    readonly_fields     = ['created_at', 'processed_at']
    list_select_related = ['seller',]
    actions             = ['approve_requests', 'reject_requests']

    # @admin.display(description='Status')
    # def status_label(self, obj):
    #     return obj.get_status_display()

    @admin.action(description="Approve selected credit requests")
    def approve_requests(self, request, queryset):
        for cr in queryset.select_related('seller'):
            try:
                # Is it all making sense here?!
                cr.approve()
                self.message_user(
                    request,
                    f" Approved #{cr.pk} (Seller: {cr.seller.username})",
                    level=messages.SUCCESS
                )
            except ValidationError as e:
                self.message_user(
                    request,
                    f" Could not approve #{cr.pk}: {e}",
                    level=messages.ERROR
                )

    @admin.action(description="Reject selected credit requests")
    def reject_requests(self, request, queryset):
        for cr in queryset.select_related('seller'):
            try:
                cr.reject()
                self.message_user(
                    request,
                    f" Rejected #{cr.pk} (Seller: {cr.seller.username})",
                    level=messages.SUCCESS
                )
            except ValidationError as e:
                self.message_user(
                    request,
                    f" Could not reject #{cr.pk}: {e}",
                    level=messages.ERROR
                )

    def save_model(self, request, obj, form, change):
        
        if change:
            old = CreditRequest.objects.get(pk=obj.pk)

            # Block any transition from APPROVED or REJECTED → PENDING
            if old.status in (Status.APPROVED, Status.REJECTED):
                self.message_user(
                    request,
                    " You cannot change the status of a processed request.",
                    level=messages.ERROR
                )
                return
            
            # PENDING → APPROVED in the form
            if old.status == Status.PENDING and obj.status == Status.APPROVED:
                try:
                    obj.approve()
                except Exception as e:
                    self.message_user(request, f" Could not approve: {e}", level=messages.ERROR)
                    return
                return

            # PENDING → REJECTED in the form
            if old.status == Status.PENDING and obj.status == Status.REJECTED:
                try:
                    obj.reject()
                except Exception as e:
                    self.message_user(request, f" Could not reject: {e}", level=messages.ERROR)
                    return
                return
        super().save_model(request, obj, form, change)

@admin.register(PhoneCharge)
class PhoneChargeAdmin(admin.ModelAdmin):
    list_display = ['id', 'seller', 'phone_number', 'amount', 'created_at']
    search_fields = ['seller__username', 'phone_number__number']
    list_filter = ['created_at']
