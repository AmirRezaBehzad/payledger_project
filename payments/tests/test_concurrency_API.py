# import threading
# import time
# import requests

# from django.test import LiveServerTestCase
# from django.contrib.auth import get_user_model
# from requests.adapters import HTTPAdapter
# from urllib3.util.retry import Retry

# from payments.models import PhoneNumber


# User = get_user_model()

# class ConcurrentPhoneChargeAPITest(LiveServerTestCase):
#     """
#     Fire N concurrent HTTP POSTs to the phone-charge API,
#     bypassing direct model calls.
#     """

#     def setUp(self):
#         # Create a user with a known balance

#         self.initial_balance = 500
#         self.user = User.objects.create_user(
#             username="api_concurrent", 
#             password="pass1234", 
#             phone_number="09121230000", 
#             balance=self.initial_balance
#         )
#         self.phone = PhoneNumber.objects.create(
#             number="09121230000", 
#             name="APILine", 
#             balance=0
#         )

#         token_url = f"{self.live_server_url}/api-token-auth/"
#         resp = requests.post(token_url, json={
#             "username": "api_concurrent",
#             "password": "pass1234"
#         })

#         print(resp)

#         resp.raise_for_status()

#         print("Hello men")

#         self.token = resp.json()["token"]

#         print("Hello boy")

#         self.headers = {"Authorization": f"Token {self.token}"}

#         print("Hello girl")

#         # 2) Define the target API URL
#         self.charge_url = f"{self.live_server_url}/api/payments/phone-charge/"

#     def _worker(self, amount, results, idx):
#         """
#         Each thread does one HTTP POST to /api/payments/phone-charge/
#         """
#         try:
#             r = requests.post(
#                 self.charge_url,
#                 json={"phone_number": self.phone.id, "amount": amount},
#                 headers=self.headers,
#                 timeout=5
#             )
#             results[idx] = r.status_code
#         except Exception as e:
#             results[idx] = f"EXC:{type(e).__name__}"

#     def test_concurrent_phone_charges(self):
#         n = 100
#         threads = []
#         results = [None] * n

#         # Launch n threads, each charging $1
#         for i in range(n):
#             t = threading.Thread(target=self._worker, args=(1.00, results, i))
#             threads.append(t)
#             t.start()
#             time.sleep(0.005)  # small jitter to spread them out

#         # Wait for all to finish
#         for t in threads:
#             t.join()

#         # Refresh from DB
#         self.user.refresh_from_db()
#         self.phone.refresh_from_db()

#         # Count HTTP 200 successes vs any errors
#         success_count = results.count(200)
#         failure_count = len([r for r in results if r != 200])

#         # All requests should succeed
#         self.assertEqual(success_count, n, f"Expected {n} successes, got: {results}")
#         self.assertEqual(failure_count, 0,       f"Failures: {results}")

#         # Final balances
#         self.assertEqual(self.user.balance,  self.initial_balance - n * 1.00)
#         self.assertEqual(self.phone.balance,             n * 1.00)


# class ConnectionPoolingConcurrentPhoneChargeAPITest(LiveServerTestCase):
#     """
#     Same as above but re-uses one requests.Session() with a custom HTTPAdapter
#     to pool connections and retry transient errors.
#     """

#     def setUp(self):
#         self.initial_balance = 500
#         self.user = User.objects.create_user(
#             username="api_pool", 
#             password="pass1234", 
#             phone_number="09121230001", 
#             balance=self.initial_balance
#         )
#         self.phone = PhoneNumber.objects.create(
#             number="09121230001", 
#             name="PoolAPILine", 
#             balance=0
#         )

#         # Get JWT token
#         token_url = f"{self.live_server_url}/api-token-auth/"
#         resp = requests.post(token_url, json={
#             "username": "api_pool",
#             "password": "pass1234"
#         })
#         resp.raise_for_status()
#         token = resp.json()["token"]            # note: "token", not "access"
#         self.headers = {"Authorization": f"Token {token}"}

#         # Prepare a session with retries & pooling
#         self.session = requests.Session()
#         retry = Retry(total=3, backoff_factor=0.1,
#                       status_forcelist=[500,502,503,504])
#         adapter = HTTPAdapter(pool_connections=50, pool_maxsize=200,
#                               max_retries=retry)
#         self.session.mount("http://", adapter)
#         self.session.mount("https://", adapter)

#         self.charge_url = f"{self.live_server_url}/api/payments/phone-charge/"

#     def _worker(self, amount, results, idx):
#         try:
#             r = self.session.post(
#                 self.charge_url,
#                 json={"phone_number": self.phone.id, "amount": amount},
#                 headers=self.headers,
#                 timeout=5
#             )
#             results[idx] = r.status_code
#         except Exception as e:
#             results[idx] = f"EXC:{type(e).__name__}"

#     def test_pooled_concurrent_phone_charges(self):
#         num_requests = 50
#         threads = []
#         results = [None] * num_requests

#         for i in range(num_requests):
#             t = threading.Thread(
#                 target=self._worker, args=(10.00, results, i)
#             )
#             threads.append(t)
#             t.start()
#             time.sleep(0.005)

#         for t in threads:
#             t.join()

#         self.user.refresh_from_db()
#         self.phone.refresh_from_db()

#         success_count = results.count(200)
#         failure_count = len([r for r in results if r != 200])

#         # All should succeed
#         self.assertEqual(success_count, num_requests,
#                          f"Expected {num_requests} successes, got: {results}")
#         self.assertEqual(failure_count, 0,
#                          "There should be no HTTP failures")
#         # Final balances
#         self.assertEqual(self.user.balance,
#                          self.initial_balance - num_requests * 10.00)
#         self.assertEqual(self.phone.balance,
#                          num_requests * 10.00)
from django.test import LiveServerTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from payments.models import PhoneNumber

User = get_user_model()

class ConcurrentPhoneChargeAPITest(LiveServerTestCase):
    def setUp(self):
        # Create seller user with initial balance
        self.initial_balance = 10000.00
        self.user = User.objects.create_user(
            username="test_seller",
            password="pass1234",
            balance=self.initial_balance
        )
        # Create a phone number entry
        self.phone = PhoneNumber.objects.create(
            number="09121234567",
            name="Test Phone",
            balance=0.00
        )

        # Setup APIClient with token auth
        self.client = APIClient()
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=self.user)
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
        import threading

        threads = []
        for i in range(num_requests):
            t = threading.Thread(target=self._worker, args=(charge_amount, results, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Refresh user and phone balances after all charges
        self.user.refresh_from_db()
        self.phone.refresh_from_db()

        # Check all requests succeeded (HTTP 200)
        success_count = results.count(200)
        failure_count = len([r for r in results if r != 200])

        self.assertEqual(success_count, num_requests, f"Expected all {num_requests} successes, got: {results}")
        self.assertEqual(failure_count, 0, f"Failures occurred: {results}")

        # Validate balances: user balance decreased and phone balance increased accordingly
        expected_user_balance = self.initial_balance - (num_requests * charge_amount)
        expected_phone_balance = num_requests * charge_amount

        self.assertAlmostEqual(float(self.user.balance), expected_user_balance, places=2)
        self.assertAlmostEqual(float(self.phone.balance), expected_phone_balance, places=2)

