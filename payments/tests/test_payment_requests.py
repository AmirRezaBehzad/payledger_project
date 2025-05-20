# payments/tests/test_payment_requests.py

from django.test import TestCase
from rest_framework.test import APIClient
from sellers.models import Seller
from payments.models import CreditRequest, PhoneNumber, Transaction
from django.urls import reverse

class TestPaymentRequests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller1 = Seller.objects.create_user(username='seller1', password='pass123', phone_number='09111111111')
        self.seller2 = Seller.objects.create_user(username='seller2', password='pass456', phone_number='09222222222')
        self.phone = PhoneNumber.objects.create(number='09333333333', name='TestLine')

    def authenticate(self, seller):
        self.client.force_authenticate(user=seller)

    def test_credit_and_charge_flow(self):
        self.authenticate(self.seller1)

        # Step 1: Add 10 credit requests
        for _ in range(10):
            CreditRequest.objects.create(seller=self.seller1, amount=100, status=1, approved_at="2024-01-01", processed=True)
            self.seller1.balance += 100
        self.seller1.save()

        # Step 2: Charge the phone 1000 times (1 unit each)
        for _ in range(1000):
            response = self.client.post("/api/phone-charge/", {
                "seller": self.seller1.id,
                "phone_number": self.phone.id,
                "amount": "1.00"
            }, format='json')
            self.assertEqual(response.status_code, 200)

        # Step 3: Check balance after charges
        self.seller1.refresh_from_db()
        self.phone.refresh_from_db()

        self.assertEqual(float(self.seller1.balance), 0.0)
        self.assertEqual(float(self.phone.balance), 1000.0)
