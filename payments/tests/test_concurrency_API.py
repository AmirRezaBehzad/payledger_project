from django.test import LiveServerTestCase
from sellers.models import Seller
from rest_framework.test import APIClient
from payments.models import PhoneNumber
from rest_framework.authtoken.models import Token
import threading

class ConcurrentPhoneChargeAPITest(LiveServerTestCase):
    def setUp(self):

        self.initial_balance = 10000.00
        self.seller = Seller.objects.create(
            username="test_seller",
            password="pass1234",
            balance=self.initial_balance
        )

        self.phone = PhoneNumber.objects.create(
            number="09121234567",
            name="Test Phone",
            balance=0.00
        )

        # Setup APIClient with token auth
        self.client = APIClient()
        
        token, _ = Token.objects.get_or_create(user=self.seller)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def _worker(self, amount, results, index):
        # Post to the phone-charge endpoint
        data = {
            "phone_number": self.phone.id,
            "amount": amount
        }
        try:
            response = self.client.post('/api/payments/phone-charge/', data, format='json')
            results[index] = response.status_code
        except Exception as e:
            results[index] = f"EXC: {type(e).__name__}"

    def test_concurrent_phone_charges(self):
        num_requests = 100
        charge_amount = 50.00  # Adjust to ensure total fits within initial balance
        results = [None] * num_requests
        
        threads = []
        for i in range(num_requests):
            t = threading.Thread(target=self._worker, args=(charge_amount, results, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Refresh user and phone balances after all charges
        self.seller.refresh_from_db()
        self.phone.refresh_from_db()

        # Check all requests succeeded (HTTP 200)
        success_count = results.count(200)
        failure_count = len([r for r in results if r != 200])

        self.assertEqual(success_count, num_requests, f"Expected all {num_requests} successes, got: {results}")
        self.assertEqual(failure_count, 0, f"Failures occurred: {results}")

        # Validate balances: user balance decreased and phone balance increased accordingly
        expected_seller_balance = self.initial_balance - (num_requests * charge_amount)
        expected_phone_balance = num_requests * charge_amount

        self.assertEqual(self.seller.balance, expected_seller_balance)
        self.assertEqual(self.phone.balance, expected_phone_balance)