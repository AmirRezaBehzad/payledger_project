import threading
from django.test import TransactionTestCase
from sellers.models import Seller
from payments.models import PhoneNumber, PhoneCharge
import threading
from django.test import TransactionTestCase
from sellers.models import Seller
from payments.models import CreditRequest

class ConcurrentPhoneChargeFunctionTest(TransactionTestCase):

    def setUp(self):
        self.initial_balance = 1000
        self.seller = Seller.objects.create_user(
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
        try:
            pc = PhoneCharge.objects.create(
                seller=self.seller,
                phone_number=self.phone,
                amount=1.00
            )
            pc.process_charge()
            results[idx] = 200
        except Exception as e:

            results[idx] = f"EXC:{type(e).__name__}"
            print(e)

    def test_concurrent_charges(self):
        n = 100
        threads = []
        results = [None] * n

        for i in range(n):
            t = threading.Thread(target=self._worker, args=(i, results))
            threads.append(t)
            t.start()
            #time.sleep(0.01)  # slight delay to stagger thread starts


        for t in threads:
            t.join()

        self.seller.refresh_from_db()
        self.phone.refresh_from_db()

        success = results.count(200)
        failures = len([r for r in results if r != 200])
        print(results)

        self.assertEqual(success, n,    f"{success=} should be {n}")
        self.assertEqual(failures, 0,   f"{failures=} should be 0")

        self.assertEqual(self.seller.balance, self.initial_balance - n * 1.00)
        self.assertEqual(self.phone.balance,   n * 1.00)

class ConnectionPoolingConcurrentPhoneChargeFunctionTest(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.initial_balance = 5000
        self.seller = Seller.objects.create_user(
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

        self.assertEqual(self.seller.balance, self.initial_balance - n * 50.00)
        self.assertEqual(self.phone.balance,   n * 50.00)


class SimpleConcurrentApproveTest(TransactionTestCase):
    def setUp(self):

        self.seller = Seller.objects.create_user(
            username="concurrent_seller",
            password="pass1234",
            phone_number="09121234568",
            balance=0,
        )

        self.credit_requests = []
        for _ in range(5):
            cr = CreditRequest.objects.create(
                seller=self.seller,
                amount=100,
                status=0,  # Pending
            )
            self.credit_requests.append(cr)

    def _approve_credit(self, cr, results, idx):
        try:
            cr.approve()
            results[idx] = "approved"
        except Exception as e:
            results[idx] = f"error: {type(e).__name__}"
            print(e)

    def test_concurrent_approves(self):
        results = [None] * len(self.credit_requests)
        threads = []

        for i, cr in enumerate(self.credit_requests):
            t = threading.Thread(target=self._approve_credit, args=(cr, results, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.seller.refresh_from_db()

        approved_count = results.count("approved")
        error_count = len([r for r in results if r != "approved"])

        self.assertEqual(approved_count, len(self.credit_requests), f"All should be approved, got: {results}")
        self.assertEqual(error_count, 0, f"No errors expected, got: {results}")

        expected_balance = 100 * len(self.credit_requests)
        self.assertEqual(self.seller.balance, expected_balance)
