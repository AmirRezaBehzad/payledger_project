from django.urls import path
from .views import CreditRequestCreateAPIView, PhoneChargeAPIView, TransactionCreateAPIView

urlpatterns = [
    path('transactions/', TransactionCreateAPIView.as_view(), name='transaction-create'),
    path('credit-requests/', CreditRequestCreateAPIView.as_view(), name='credit-request-create'),
    path('phone-charge/', PhoneChargeAPIView.as_view(), name='phone-charge'),
]