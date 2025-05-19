from django.db import models
from django.utils import timezone
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F


class Status(models.IntegerChoices):
    PENDING  = 0, 'Pending'
    APPROVED = 1, 'Approved'
    REJECTED = 2, 'Rejected'


class Seller(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Seller {self.phone_number} - Balance: {self.balance}"


class CreditRequest(models.Model):
    seller      = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        related_name='credit_requests'
    )
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    status      = models.IntegerField(
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"CreditRequest {self.id} for Seller {self.seller.phone_number} "
            f"- Status: {Status(self.status).label}"
        )

    def approve(self):
        if self.status != Status.PENDING:
            raise ValueError("Only pending requests can be approved")
        self.status = Status.APPROVED
        # approved_at will be set by save()
        self.save()

    def reject(self):
        if self.status != Status.PENDING:
            raise ValueError("Only pending requests can be rejected")
        self.status = Status.REJECTED
        self.save()

    def save(self, *args, **kwargs):
        # 1) Grab old status (None on first create)
        old_status = None
        if self.pk:
            old_status = CreditRequest.objects.get(pk=self.pk).status

        # 2) Do the normal save
        super().save(*args, **kwargs)

        # 3) If we’ve just transitioned into APPROVED for the first time…
        if (
            self.status == Status.APPROVED
            and old_status != Status.APPROVED
            and self.approved_at is None
        ):
            with transaction.atomic():
                # a) Lock & bump seller balance
                seller = Seller.objects.select_for_update().get(pk=self.seller.pk)
                seller.balance = F('balance') + self.amount
                seller.save()

                # b) Log the transaction
                Transaction.objects.create(
                    seller=seller,
                    amount=self.amount,
                    transaction_type='credit',
                    description=f"Admin-approved CreditRequest #{self.id}"
                )

                # c) Record approved_at to prevent double‐billing
                self.approved_at = timezone.now()
                super().save(update_fields=['approved_at'])


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
