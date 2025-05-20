from django.shortcuts import render
from django.db import transaction
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction as db_transaction
from .models import Seller, Transaction, PhoneNumber
from .serializers import SellerSerializer, TransactionSerializer, CreditRequestSerializer, PhoneChargeSerializer
from rest_framework.permissions import IsAuthenticated
from .serializers import SellerSerializer, SellerRegistrationSerializer

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

class TransactionCreateAPIView(APIView):
    @db_transaction.atomic
    def post(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            seller_id = serializer.validated_data['seller'].id
            amount = serializer.validated_data['amount']
            transaction_type = serializer.validated_data['transaction_type']

            try:
                # Lock the seller record for update to prevent race condition
                seller = Seller.objects.select_for_update().get(id=seller_id)
            except Seller.DoesNotExist:
                return Response({"error": "Seller not found"}, status=status.HTTP_404_NOT_FOUND)

            # Check balance for debit transactions
            if transaction_type == 'debit' and seller.balance < amount:
                return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

            # Update seller balance
            if transaction_type == 'credit':
                seller.balance += amount
            else:  # debit
                seller.balance -= amount
            seller.save()

            # Save transaction record
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreditRequestCreateAPIView(APIView):
    def post(self, request):
        serializer = CreditRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Creates request but does not increase balance yet
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PhoneChargeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 1) Validate input or raise 400
        serializer = PhoneChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2) Extract IDs from validated data
        seller_id      = serializer.validated_data['seller'].pk
        phone_id       = serializer.validated_data['phone_number'].pk
        amount         = serializer.validated_data['amount']

        # 3) Lock both rows
        seller = Seller.objects.select_for_update().get(pk=seller_id)
        phone  = PhoneNumber.objects.select_for_update().get(pk=phone_id)

        # 4) Double-check balance
        if seller.balance < amount:
            return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

        # 5) Move the money
        seller.balance -= amount
        seller.save(update_fields=['balance'])

        phone.balance += amount
        phone.save(update_fields=['balance'])

        # 6) Log the transaction
        Transaction.objects.create(
            seller=seller,
            amount=amount,
            transaction_type='debit',
            description=f"Charged phone {phone.number} ({phone.name or 'no name'})"
        )

        # 7) Return the new balances
        return Response({
            "message":        "Phone number charged successfully.",
            "seller_balance": str(seller.balance),
            "phone_balance":  str(phone.balance),
        }, status=status.HTTP_200_OK)
