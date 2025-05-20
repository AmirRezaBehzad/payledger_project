# payments/tests/test_concurrency.py

from django.test import TransactionTestCase
from rest_framework.test import APIClient
from sellers.models import Seller
from payments.models import PhoneNumber, CreditRequest
from threading import Thread
import time

class TestConcurrency(TransactionTestCase):
    reset_sequences = True  # Ensures fresh IDs in DB

    def setUp(self):
        self.client = APIClient()
        self.seller = Seller.objects.create_user(username='sellerX', password='passX', phone_number='09999999999')
        self.phone = PhoneNumber.objects.create(number='09399999999', name='LineX')

        # Pre-top up balance (single credit)
        CreditRequest.objects.create(seller=self.seller, amount=1000, status=1, approved_at="2024-01-01", processed=True)
        self.seller.balance = 1000
        self.seller.save()

    def charge_phone(self):
        client = APIClient()
        client.force_authenticate(user=self.seller)

        for _ in range(100):  # Each thread will run 100 times
            client.post("/api/phone-charge/", {
                "seller": self.seller.id,
                "phone_number": self.phone.id,
                "amount": "1.00"
            }, format='json')

    def test_concurrent_phone_charging(self):
        threads = [Thread(target=self.charge_phone) for _ in range(10)]  # 10 threads × 100 = 1000 charges

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.seller.refresh_from_db()
        self.phone.refresh_from_db()

        self.assertEqual(float(self.seller.balance), 0.0)
        self.assertEqual(float(self.phone.balance), 1000.0)
