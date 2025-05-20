# payments/tests/test_payment_requests.py

from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from sellers.models import Seller
from payments.models import PhoneNumber

class TestPaymentRequests(APITestCase):
    def setUp(self):
        # Create two sellers and a phone number
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
        self.phone = PhoneNumber.objects.create(
            number='09333333333',
            name='TestLine',
            balance=Decimal('0.00'),
        )

    def test_credit_and_charge_flow(self):
        # 1) Authenticate as seller1
        self.client.force_authenticate(user=self.seller1)

        # 2) Credit seller1 ten times via transaction API
        url_credit = reverse('transaction-create')
        for _ in range(10):
            resp = self.client.post(
                url_credit,
                {
                    'seller': self.seller1.id,
                    'amount': '100.00',
                    'transaction_type': 'credit',
                },
                format='json'
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # 3) Refresh seller1 and re-authenticate so serializer.validate() sees updated balance
        self.seller1.refresh_from_db()
        self.client.force_authenticate(user=self.seller1)

        # 4) Charge the phone 1000 times via the phone-charge API
        url_charge = reverse('phone-charge')
        for _ in range(1000):
            resp = self.client.post(
                url_charge,
                {
                    'phone_number': self.phone.id,
                    'amount': '1.00',
                },
                format='json'
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # 5) Verify final balances
        self.seller1.refresh_from_db()
        self.phone.refresh_from_db()
        self.assertEqual(self.seller1.balance, Decimal('0.00'))
        self.assertEqual(self.phone.balance, Decimal('1000.00'))

