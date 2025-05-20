from django.shortcuts import render
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from sellers.serializers import SellerSerializer, SellerRegistrationSerializer
from .models import Seller
# Create your views here.
class SellerListCreateAPIView(APIView):
    # Anyone can register; you could tighten GET with IsAuthenticated if you like
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sellers = Seller.objects.all()
        serializer = SellerSerializer(sellers, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Use the registration serializer that handles set_password()
        serializer = SellerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seller = serializer.save()
        # Return the public representation via SellerSerializer
        out = SellerSerializer(seller)
        return Response(out.data, status=status.HTTP_201_CREATED)