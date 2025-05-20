from decimal import Decimal
from django.urls import reverse
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework import status
from concurrent.futures import ThreadPoolExecutor
from sellers.models import Seller
from payments.models import PhoneNumber

class TestConcurrency(TransactionTestCase):
    reset_sequences = True  # ensures fresh primary keys

    def setUp(self):
        # Seed a seller with initial balance of 1000
        self.seller = Seller.objects.create_user(
            username='sellerX', password='passX', phone_number='09999999999', balance=Decimal('1000.00')
        )
        self.phone = PhoneNumber.objects.create(
            number='09399999999', name='LineX', balance=Decimal('0.00')
        )

    def _charge_once(self):
        # each thread uses its own client
        client = APIClient()
        client.force_authenticate(user=self.seller)
        url_charge = reverse('phone-charge')
        resp = client.post(
            url_charge,
            {'phone_number': self.phone.id, 'amount': '1.00'},
            format='json'
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_concurrent_phone_charging(self):
        # 1000 parallel charges via 50 threads
        with ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(lambda _: self._charge_once(), range(1000)))

        self.seller.refresh_from_db()
        self.phone.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal('0.00'))
        self.assertEqual(self.phone.balance, Decimal('1000.00'))