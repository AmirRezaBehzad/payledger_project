from django.shortcuts import render
from django.db import transaction
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction as db_transaction
from .models import Seller, Transaction, PhoneNumber
from rest_framework.permissions import IsAuthenticated
from sellers.serializers import SellerSerializer, SellerRegistrationSerializer
from .serializers import TransactionSerializer, CreditRequestSerializer, PhoneChargeSerializer


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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreditRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(seller=request.user)   # ✅ Inject authenticated user as seller
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PhoneChargeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 1) Validate without passing seller in the body
        serializer = PhoneChargeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        phone = PhoneNumber.objects.select_for_update().get(pk=serializer.validated_data['phone_number'].pk)
        amount = serializer.validated_data['amount']
        seller = Seller.objects.select_for_update().get(pk=request.user.pk)

        # 2) Check balance
        if seller.balance < amount:
            return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

        # 3) Perform transfer
        seller.balance -= amount
        seller.save(update_fields=['balance'])

        phone.balance += amount
        phone.save(update_fields=['balance'])

        # 4) Log the transaction
        Transaction.objects.create(
            seller=seller,
            amount=amount,
            transaction_type='debit',
            description=f"Charged phone {phone.number} ({phone.name or 'no name'})"
        )

        # 5) Return updated balances
        return Response({
            "message":        "Phone number charged successfully.",
            "seller_balance": str(seller.balance),
            "phone_balance":  str(phone.balance),
        }, status=status.HTTP_200_OK)
