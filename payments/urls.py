from django.urls import path
from .views import TransactionCreateAPIView, CreditRequestCreateAPIView, PhoneChargeAPIView

urlpatterns = [
    path('transactions/', TransactionCreateAPIView.as_view(), name='transaction-create'),
    path('credit-requests/', CreditRequestCreateAPIView.as_view(), name='credit-request-create'),
    path('phone-charge/', PhoneChargeAPIView.as_view(), name='phone-charge'),
]
