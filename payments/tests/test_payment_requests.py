from decimal import Decimal
from django.test import TestCase
from django.db.models import F
from django.core.exceptions import ValidationError

from sellers.models import Seller
from payments.models import Transaction, PhoneNumber, PhoneCharge

class TransactionAndChargeModelTests(TestCase):
    def setUp(self):

        self.seller1 = Seller.objects.create_user(
            username='seller1',
            password='pass123',
            phone_number='09111111111',
            balance=Decimal('0.00'),
        )
        self.seller2 = Seller.objects.create_user(
            username='seller2',
            password='pass456',
            phone_number='09222222222',
            balance=Decimal('0.00'),
        )

        self.phone1 = PhoneNumber.objects.create(
            number='09333333333',
            name='TestLine1',
            balance=Decimal('0.00'),
        )
        self.phone2 = PhoneNumber.objects.create(
            number='09444444444',
            name='TestLine2',
            balance=Decimal('0.00'),
        )

    def test_credit_and_charge_flow_two_sellers(self):

        for _ in range(10):
            for seller in [self.seller1, self.seller2]:
                Transaction.objects.create(
                    seller=seller,
                    amount=Decimal('100.00'),
                    transaction_type='credit',
                    description='Test credit'
                )
                Seller.objects.filter(pk=seller.pk).update(
                    balance=F('balance') + Decimal('100.00')
                )

        self.seller1.refresh_from_db()
        self.seller2.refresh_from_db()
        self.assertEqual(self.seller1.balance, Decimal('1000.00'))
        self.assertEqual(self.seller2.balance, Decimal('1000.00'))

        for _ in range(500):
            charge1 = PhoneCharge.objects.create(
                seller=self.seller1,
                phone_number=self.phone1,
                amount=Decimal('1.00')
            )
            charge1.process_charge()

            charge2 = PhoneCharge.objects.create(
                seller=self.seller2,
                phone_number=self.phone2,
                amount=Decimal('1.00')
            )
            charge2.process_charge()
 
        self.seller1.refresh_from_db()
        self.phone1.refresh_from_db()
        self.seller2.refresh_from_db()
        self.phone2.refresh_from_db()

        self.assertEqual(self.seller1.balance, Decimal('500.00'))
        self.assertEqual(self.phone1.balance, Decimal('500.00'))
        self.assertEqual(self.seller2.balance, Decimal('500.00'))
        self.assertEqual(self.phone2.balance, Decimal('500.00'))
