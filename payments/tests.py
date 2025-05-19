from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Seller, Transaction

# Existing model tests
class SellerModelTest(TestCase):
    def test_create_seller(self):
        seller = Seller.objects.create(phone_number='09121234567', balance=1000)
        self.assertEqual(seller.phone_number, '09121234567')
        self.assertEqual(seller.balance, 1000)

class TransactionModelTest(TestCase):
    def test_create_transaction(self):
        seller = Seller.objects.create(phone_number='09998887766', balance=2000)
        transaction = Transaction.objects.create(
            seller=seller,
            amount=500,
            transaction_type='credit',
            description='Test credit'
        )
        self.assertEqual(transaction.seller, seller)
        self.assertEqual(transaction.amount, 500)
        self.assertEqual(transaction.transaction_type, 'credit')

# New API tests
class SellerAPITest(APITestCase):
    def test_create_seller(self):
        url = reverse('seller-list-create')
        data = {'phone_number': '09123456789', 'balance': '1000.00'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['phone_number'], '09123456789')

class TransactionAPITest(APITestCase):
    def setUp(self):
        self.seller = Seller.objects.create(phone_number='09998887766', balance=1500)

    def test_create_credit_transaction(self):
        url = reverse('transaction-create')
        data = {
            'seller': self.seller.id,
            'amount': '500.00',
            'transaction_type': 'credit',
            'description': 'Credit test'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.seller.refresh_from_db()
        self.assertEqual(float(self.seller.balance), 2000.00)

    def test_create_debit_transaction_insufficient_balance(self):
        url = reverse('transaction-create')
        data = {
            'seller': self.seller.id,
            'amount': '2000.00',
            'transaction_type': 'debit',
            'description': 'Debit test'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
