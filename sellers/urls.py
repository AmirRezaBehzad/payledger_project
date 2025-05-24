from django.urls import path
from .views import SellerListCreateAPIView, SellerProfileAPIView

urlpatterns = [
    path('', SellerListCreateAPIView.as_view(), name='seller-list-create'),
    path('profile/', SellerProfileAPIView.as_view(), name='seller-profile'),
]