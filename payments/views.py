from django.shortcuts import render
from django.db import transaction
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction as db_transaction
from .models import Seller, Transaction
from .serializers import SellerSerializer, TransactionSerializer, CreditRequestSerializer, PhoneChargeSerializer

class SellerListCreateAPIView(APIView):
    def get(self, request):
        sellers = Seller.objects.all()
        serializer = SellerSerializer(sellers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SellerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    @transaction.atomic
    def post(self, request):
        serializer = PhoneChargeSerializer(data=request.data)
        if serializer.is_valid():
            seller = serializer.validated_data['seller']
            phone_number = serializer.validated_data['phone_number']
            amount = serializer.validated_data['amount']

            seller = Seller.objects.select_for_update().get(pk=seller.pk)

            if seller.balance < amount:
                return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

            # کم کردن مبلغ از اعتبار فروشنده
            seller.balance -= amount
            seller.save()

            # اضافه کردن مبلغ به موجودی شماره تلفن
            phone_number.balance += amount
            phone_number.save()

            # ثبت تراکنش کاهش اعتبار
            Transaction.objects.create(
                seller=seller,
                amount=amount,
                transaction_type='debit',
                description=f"Charged phone number {phone_number.number} ({phone_number.name})"
            )

            return Response({
                "message": "Phone number charged successfully.",
                "phone_number": phone_number.number,
                "phone_name": phone_number.name,
                "amount": str(amount),
                "seller_balance": str(seller.balance),
                "phone_balance": str(phone_number.balance),  # نمایش موجودی شماره تلفن
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
