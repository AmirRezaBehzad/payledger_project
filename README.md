# PayLedger Project

**PayLedger** is a Django-based backend application that enables sellers to manage credit requests, phone charging operations, and track all related transactions in a secure and concurrent environment.

## 🚀 Features

- Seller registration and authentication (via token-based auth)
- API endpoints to:
  - Submit and approve/reject credit requests
  - Charge phone numbers (debits seller and credits phone)
  - View transaction history per seller
- Admin panel for managing models
- Thread-safe logic for balance updates with concurrent tests
- Clean and modular Django app structure (`payments`, `sellers`)

## 🛠 Project Structure

```
payledger_project-main/
├── manage.py
├── payledger_project/         # Project settings
├── payments/                  # PhoneCharge, CreditRequest, Transaction APIs
├── sellers/                   # Seller model and auth logic
```

## ⚙️ Installation

1. **Clone the repository:**

```bash
git clone https://github.com/your-username/payledger_project.git
cd payledger_project
```

2. **Create and activate a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt  # (Add this file if not already present)
```

4. **Apply migrations:**

```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create a superuser (optional for admin access):**

```bash
python manage.py createsuperuser
```

6. **Run the development server:**

```bash
python manage.py runserver
```

## 🔐 Authentication

- Token-based authentication is used (`rest_framework.authtoken`).
- After registering a seller, obtain a token via:

```
POST /api-token-auth/
```

- Include it in headers:

```
Authorization: Token <your_token>
```

## 🧪 Running Tests

Includes concurrency tests using `TransactionTestCase` and `LiveServerTestCase`:

```bash
python manage.py test
```

These tests ensure thread-safe balance updates across concurrent operations like phone charging.

## 📫 API Endpoints

| Method | Endpoint                     | Description                        |
|--------|------------------------------|------------------------------------|
| POST   | /api-token-auth/             | Get auth token                     |
| POST   | /api/sellers/                | Register new seller                |
| GET    | /api/sellers/                | List sellers (auth required)       |
| POST   | /api/payments/phone-charge/  | Charge a phone number              |
| POST   | /api/payments/credit-requests/ | Create a credit request          |
| GET    | /api/payments/transactions/  | List transactions for seller       |

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
