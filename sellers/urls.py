from django.urls import path
from .views import SellerListCreateAPIView

urlpatterns = [
    path('', SellerListCreateAPIView.as_view(), name='seller-list-create'),
]