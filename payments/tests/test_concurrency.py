# import os
# import requests
# import threading
# import time
# from django.test import LiveServerTestCase
# from django.contrib.auth import get_user_model
# from requests.adapters import HTTPAdapter
# from urllib3.util.retry import Retry
# from payments.models import PhoneNumber, CreditRequest

# User = get_user_model()


# def wait_for_server(url, timeout=30, interval=0.5):
#     start = time.time()
#     while time.time() - start < timeout:
#         try:
#             r = requests.get(url, timeout=2)
#             print(f"[wait_for_server] GET {url} → {r.status_code}")
#             print(f"[wait_for_server] body: {r.text!r}")
#             if r.status_code < 500:   # any response means "up"
#                 return
#         except Exception as e:
#             print(f"[wait_for_server] error connecting: {e!r}")
#         time.sleep(interval)
#     raise RuntimeError(f"❌ Test server not responding at: {url}")

# class ConcurrentPhoneChargeAPITest(LiveServerTestCase):
#     def setUp(self):
#         # 1) Create test seller & phone
#         self.initial_balance = 1000
#         self.seller = User.objects.create_user(
#             username="concurrent",
#             password="pass1234",
#             phone_number="09121234567",
#             balance=self.initial_balance,
#         )
#         self.phone = PhoneNumber.objects.create(
#             number="09121234567", name="TestLine", balance=0
#         )

#         # 2) Wait for the auth endpoint to be ready
#         auth_url = f"{self.live_server_url}/api-token-auth/"
#         print("Live server URL:", self.live_server_url)
#         print("Auth endpoint:", auth_url)
#         wait_for_server(auth_url, timeout=30)

#         # 3) Obtain token
#         payload = {"username": "concurrent", "password": "pass1234"}
#         print("[AUTH] Payload:", payload)
#         r = requests.post(auth_url, json=payload, timeout=60)
#         print("[AUTH] Response status:", r.status_code)
#         print("[AUTH] Response body:", r.text)
#         r.raise_for_status()
#         token = r.json().get("token")
#         print("[AUTH] Obtained token:", token)

#         # 4) Store auth header
#         self.headers = {"Authorization": f"Token {token}"}

#     def _worker(self, idx, results):
#         url = f"{self.live_server_url}/api/payments/phone-charge/"
#         body = {"phone_number": self.phone.id, "amount": "1.00"}
#         try:
#             r = requests.post(url, json=body, headers=self.headers, timeout=120)
#             results[idx] = r.status_code
#             if r.status_code != 200:
#                 print(f"[WORKER {idx}] status {r.status_code}, body: {r.text}")
#         except Exception as e:
#             results[idx] = f"EXC:{type(e).__name__}"
#             print(f"[WORKER {idx}] exception: {e!r}")

#     def test_concurrent_charges(self):
#         # ⚙️ Adjusted to 200 threads and 200 results slots
#         n = 100
#         threads = []
#         results = [None] * n

#         for i in range(n):
#             t = threading.Thread(target=self._worker, args=(i, results))
#             t.start()
#             threads.append(t)
#         for t in threads:
#             t.join()

#         # Refresh balances from DB
#         self.seller.refresh_from_db()
#         self.phone.refresh_from_db()

#         # 🔍 Check outcomes
#         success = results.count(200)
#         failures = len([r for r in results if r != 200])

#         # ✅ Expect exactly n successes, no failures
#         self.assertEqual(success, n, f"{success=} should be {n}")
#         self.assertEqual(failures, 0, f"{failures=} should be 0")

#         # 💰 Balance checks: each thread charged 1.00
#         expected_phone_balance = n * 1.00
#         expected_seller_balance = self.initial_balance - expected_phone_balance

#         self.assertEqual(self.phone.balance, expected_phone_balance)
#         self.assertEqual(self.seller.balance, expected_seller_balance)


# class ConnectionPoolingConcurrentPhoneChargeAPITest(LiveServerTestCase):
#     def setUp(self):
#         # 1) Create pooled seller & phone
#         self.seller = User.objects.create_user(
#             username="pooled",
#             password="pass1234",
#             phone_number="09999999999",
#             balance=10000
#         )
#         self.phone = PhoneNumber.objects.create(
#             number="09999999999", name="PoolLine", balance=0
#         )
#         time.sleep(0.1)

#         # 2) Obtain token with a session that ignores proxies
#         auth_url = f"{self.live_server_url}/api-token-auth/"
#         print("Auth endpoint (pooled):", auth_url)
#         payload = {"username": "pooled", "password": "pass1234"}
#         print("[AUTH-POOL] Payload:", payload)

#         session = requests.Session()
#         session.trust_env = False

#         r = session.post(auth_url, json=payload, timeout=5)
#         print("[AUTH-POOL] Response status:", r.status_code)
#         print("[AUTH-POOL] Response body:", r.text)
#         r.raise_for_status()
#         token = r.json().get("token")
#         print("[AUTH-POOL] Obtained token:", token)

#         # 3) Setup connection-pooled session for workers
#         self.session = requests.Session()
#         self.session.trust_env = False
#         retry = Retry(
#             total=3,
#             backoff_factor=0.2,
#             status_forcelist=[500, 502, 503, 504]
#         )
#         adapter = HTTPAdapter(
#             pool_connections=100,
#             pool_maxsize=1000,
#             max_retries=retry
#         )
#         self.session.mount("http://", adapter)
#         self.session.mount("https://", adapter)

#         self.headers = {"Authorization": f"Token {token}"}
#         self.url = f"{self.live_server_url}/api/payments/phone-charge/"

#     def _worker(self, idx, results):
#         body = {"phone_number": self.phone.id, "amount": "100.00"}
#         try:
#             r = self.session.post(
#                 self.url,
#                 json=body,
#                 headers=self.headers,
#                 timeout=5
#             )
#             results[idx] = r.status_code
#             if r.status_code != 200:
#                 print(
#                     f"[POOL WORKER {idx}] status {r.status_code}, body: {r.text}"
#                 )
#         except Exception as e:
#             results[idx] = f"EXC:{type(e).__name__}"
#             print(f"[POOL WORKER {idx}] exception: {e!r}")

#     def test_pooled_concurrent_charges(self):
#         n = 50
#         threads = []
#         results = [None] * n

#         for i in range(n):
#             t = threading.Thread(
#                 target=self._worker,
#                 args=(i, results)
#             )
#             t.start()
#             threads.append(t)
#         for t in threads:
#             t.join()

#         self.seller.refresh_from_db()
#         self.phone.refresh_from_db()

#         success = results.count(200)
#         failures = len([r for r in results if r != 200])

#         self.assertEqual(success, n, f"{success=} should be {n}")
#         self.assertEqual(failures, 0, f"{failures=} should be 0")

#         self.assertEqual(
#             self.phone.balance,
#             n * 100.00
#         )
#         self.assertEqual(
#             self.seller.balance,
#             10000 - n * 100.00
#         )

#     def test_with_functions(self):
#         credit_request = CreditRequest.objects.create(
#             seller=self.seller,
#             amount=1000
#         )
#         credit_request.approve()

import threading
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from payments.models import PhoneNumber, PhoneCharge
import time

User = get_user_model()

class ConcurrentPhoneChargeFunctionTest(TransactionTestCase):
    """
    Concurrently creates PhoneCharge instances and calls process_charge()
    directly, bypassing the HTTP layer.
    """
    reset_sequences = True  # make auto‐pks predictable

    def setUp(self):
        # 1) Create seller with 1000 in balance, and an empty phone line
        self.initial_balance = 1000
        self.seller = User.objects.create_user(
            username="concurrent",
            password="pass1234",
            phone_number="09121234567",
            balance=self.initial_balance,
        )
        self.phone = PhoneNumber.objects.create(
            number="09121234567",
            name="TestLine",
            balance=0,
        )

    def _worker(self, idx, results):
        """
        Each thread: attempts to charge 1.00 by creating a PhoneCharge
        then calling its process_charge().
        """
        try:
            pc = PhoneCharge.objects.create(
                seller=self.seller,
                phone_number=self.phone,
                amount=1.00
            )
            pc.process_charge()
            results[idx] = 200
        except Exception as e:
            # Any exception (locking failure, validation error, etc.)
            results[idx] = f"EXC:{type(e).__name__}"

    def test_concurrent_charges(self):
        n = 100
        threads = []
        results = [None] * n

        # spawn n threads
        for i in range(n):
            t = threading.Thread(target=self._worker, args=(i, results))
            threads.append(t)
            t.start()
            time.sleep(0.01)  # slight delay to stagger thread starts

        # wait for all to finish
        for t in threads:
            t.join()

        # refresh from DB
        self.seller.refresh_from_db()
        self.phone.refresh_from_db()

        # count successes vs failures
        success = results.count(200)
        failures = len([r for r in results if r != 200])

        # all should succeed
        self.assertEqual(success, n,    f"{success=} should be {n}")
        self.assertEqual(failures, 0,   f"{failures=} should be 0")

        # balances
        self.assertEqual(self.seller.balance, self.initial_balance - n * 1.00)
        self.assertEqual(self.phone.balance,   n * 1.00)


class ConnectionPoolingConcurrentPhoneChargeFunctionTest(TransactionTestCase):
    """
    Same thing, but re-uses a single Django DB connection pool across threads.
    (Requests Session not needed here — Django ORM manages its own connections.)
    """
    reset_sequences = True

    def setUp(self):
        self.initial_balance = 5000
        self.seller = User.objects.create_user(
            username="pooled",
            password="pass1234",
            phone_number="09999999999",
            balance=self.initial_balance,
        )
        self.phone = PhoneNumber.objects.create(
            number="09999999999",
            name="PoolLine",
            balance=0,
        )

    def _worker(self, idx, results):
        try:
            pc = PhoneCharge.objects.create(
                seller=self.seller,
                phone_number=self.phone,
                amount=50.00
            )
            pc.process_charge()
            results[idx] = 200
        except Exception as e:
            results[idx] = f"EXC:{type(e).__name__}"

    def test_pooled_concurrent_charges(self):
        n = 50
        threads = []
        results = [None] * n

        for i in range(n):
            t = threading.Thread(target=self._worker, args=(i, results))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.seller.refresh_from_db()
        self.phone.refresh_from_db()

        success = results.count(200)
        failures = len([r for r in results if r != 200])

        self.assertEqual(success, n,    f"{success=} should be {n}")
        self.assertEqual(failures, 0,   f"{failures=} should be 0")

        # each thread debited 50.00
        self.assertEqual(self.seller.balance, self.initial_balance - n * 50.00)
        self.assertEqual(self.phone.balance,   n * 50.00)

