from django.utils import timezone
from django.db import models, transaction
from django.db.models import F
from sellers.models import Seller

class Status(models.IntegerChoices):
    PENDING  = 0, 'Pending'
    APPROVED = 1, 'Approved'
    REJECTED = 2, 'Rejected'

class CreditRequest(models.Model):
    seller      = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='credit_requests')
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    status      = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    created_at  = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    processed   = models.BooleanField(default=False)  # INTERNAL FLAG

    def __str__(self):
        return (
            f"CreditRequest {self.id} for Seller {self.seller.username or self.seller.phone_number} "
            f"- Status: {Status(self.status).label}"
        )

    def approve(self):
        if self.status != Status.PENDING:
            raise ValueError("Only pending requests can be approved")
        self.status = Status.APPROVED
        self.save()

    def reject(self):
        if self.status != Status.PENDING:
            raise ValueError("Only pending requests can be rejected")
        self.status    = Status.REJECTED
        self.processed = True   # mark as handled so no future bump
        self.save()

    def save(self, *args, **kwargs):
        # 1) What was the status before?
        old_status = None
        if self.pk:
            old_status = CreditRequest.objects.get(pk=self.pk).status

        # 2) Persist the new status/fields
        super().save(*args, **kwargs)

        # 3) If PENDING→REJECTED, mark processed so no future bump
        if old_status == Status.PENDING and self.status == Status.REJECTED and not self.processed:
            self.processed = True
            super().save(update_fields=['processed'])

        # 4) Only on first-ever PENDING→APPROVED and not-processed
        if old_status == Status.PENDING and self.status == Status.APPROVED and not self.processed:
            with transaction.atomic():
                # a) bump seller balance
                seller = Seller.objects.select_for_update().get(pk=self.seller.pk)
                seller.balance = F('balance') + self.amount
                seller.save()

                # b) log the transaction
                Transaction.objects.create(
                    seller=seller,
                    amount=self.amount,
                    transaction_type='credit',
                    description=f"Approved CreditRequest #{self.id}"
                )

                # c) stamp approval time + processed flag
                self.approved_at = timezone.now()
                self.processed   = True
                super().save(update_fields=['approved_at', 'processed'])

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return (
            f"{self.transaction_type.capitalize()} {self.amount} "
            f"for {self.seller.phone_number} at {self.timestamp}"
        )


class PhoneNumber(models.Model):
    number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.number})"
        return self.number
