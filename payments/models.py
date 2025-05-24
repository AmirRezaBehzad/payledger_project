from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F
from sellers.models import Seller
from django.core.validators import MinValueValidator

class Status(models.IntegerChoices):
    PENDING  = 0, 'Pending'
    APPROVED = 1, 'Approved'
    REJECTED = 2, 'Rejected'

class CreditRequest(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='credit_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"#{self.pk} by {self.seller.username} — {self.get_status_display()}"

    def approve(self):

        with transaction.atomic():
            cr = CreditRequest.objects.select_for_update().get(pk=self.pk)
            if cr.status != Status.PENDING:
                raise ValidationError("Cannot approve a non-pending request.")

            # bump seller.balance
            # seller = Seller.objects.select_for_update().get(pk=cr.seller_id)
            # seller.balance = F('balance') + cr.amount
            # seller.save(update_fields=['balance'])
            Seller.objects.filter(pk=cr.seller_id).update(balance=F('balance') + cr.amount)

            # log the Transaction
            Transaction.objects.create(
                seller=cr.seller,
                amount=cr.amount,
                transaction_type='credit',
                description=f"Approved CreditRequest #{cr.pk}"
            )

            # mark as approved
            cr.status = Status.APPROVED
            cr.processed_at = timezone.now()
            cr.save(update_fields=['status', 'processed_at'])

    # def approve(self):
    #     """Approve a pending request, bump seller.balance, log a Transaction."""
    #     # cr = CreditRequest.objects.select_for_update().get(pk=self.pk)
    #     cr = CreditRequest.objects.get(pk=self.pk)
    #     if cr.status != Status.PENDING:
    #         raise ValidationError("Cannot approve a non-pending request.")

    #     # bump seller.balance
    #     # seller = Seller.objects.select_for_update().get(pk=cr.seller_id)
    #     seller = Seller.objects.get(pk=cr.seller_id)
    #     seller.balance = seller.balance + cr.amount
    #     seller.save(update_fields=['balance'])

    #     # log the Transaction
    #     Transaction.objects.create(
    #         seller=seller,
    #         amount=cr.amount,
    #         transaction_type='credit',
    #         description=f"Approved CreditRequest #{cr.pk}"
    #     )
    #     # mark as approved
    #     cr.status       = Status.APPROVED
    #     cr.processed_at = timezone.now()
    #     cr.save(update_fields=['status', 'processed_at'])

    def reject(self):
        """Reject a pending request (no balance change)."""
        with transaction.atomic():
            cr = CreditRequest.objects.select_for_update().get(pk=self.pk)
            if cr.status != Status.PENDING:
                raise ValidationError("Cannot reject a non-pending request.")

            cr.status = Status.REJECTED
            cr.processed_at = timezone.now()
            cr.save(update_fields=['status', 'processed_at'])

    # def reject(self):
    #     """Reject a pending request (no balance change)."""
    #     cr = CreditRequest.objects.select_for_update().get(pk=self.pk)
    #     if cr.status != Status.PENDING:
    #         raise ValidationError("Cannot reject a non-pending request.")

    #     cr.status       = Status.REJECTED
    #     cr.processed_at = timezone.now()
    #     cr.save(update_fields=['status', 'processed_at'])

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit',  'Debit'),
    ]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} {self.amount} for {self.seller.username} at {self.timestamp}"

class PhoneNumber(models.Model):
    number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.number})" if self.name else self.number

class PhoneCharge(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='phone_charges')
    phone_number = models.ForeignKey(PhoneNumber, on_delete=models.CASCADE, related_name='charges')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.seller.username} → {self.phone_number.number} ({self.amount})"

    def process_charge(self):
 
        with transaction.atomic():
            seller = Seller.objects.select_for_update().get(pk=self.seller.pk)
            phone = PhoneNumber.objects.select_for_update().get(pk=self.phone_number.pk)

            if seller.balance < self.amount:
                raise ValidationError("Insufficient seller balance.")

            # debit seller
            # seller.balance = F('balance') - self.amount
            # seller.save(update_fields=['balance'])
            Seller.objects.filter(pk=seller.pk).update(balance=F('balance') - self.amount)

            # credit phone
            # phone.balance = F('balance') + self.amount
            # phone.save(update_fields=['balance']) # todo : use update!
            PhoneNumber.objects.filter(pk=phone.pk).update(balance=F('balance') + self.amount)

            Transaction.objects.create(
                seller=seller,
                amount=self.amount,
                transaction_type='debit',
                description=f"Charged phone {phone.number}"
            )
            return True

    # def process_charge(self):
    #     """Debit seller.balance, credit phone_number.balance, log a Transaction."""
    #     seller = Seller.objects.get(pk=self.seller.pk)
    #     phone = PhoneNumber.objects.get(pk=self.phone_number.pk)

    #     if seller.balance < self.amount:
    #         raise ValidationError("Insufficient seller balance.")

    #     # debit seller
    #     seller.balance = seller.balance - Decimal(self.amount)
    #     seller.save(update_fields=['balance'])

    #     # credit phone
    #     phone.balance = phone.balance + Decimal(self.amount)
    #     phone.save(update_fields=['balance'])

    #     Transaction.objects.create(
    #         seller=seller,
    #         amount=self.amount,
    #         transaction_type='debit',
    #         description=f"Charged phone {phone.number}"
    #     )
    #     return True