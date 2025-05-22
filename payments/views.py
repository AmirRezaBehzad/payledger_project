from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction as db_transaction
from .models import Seller, Transaction, PhoneNumber
from rest_framework.permissions import IsAuthenticated
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
    
# payments/views.py

from django.db import transaction
from django.db.models import F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import PhoneNumber, Transaction
from sellers.models import Seller
from .serializers import PhoneChargeSerializer

# payments/views.py

from django.db import transaction
from django.db.models import F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import PhoneNumber, Transaction
from sellers.models import Seller
from .serializers import PhoneChargeSerializer


class PhoneChargeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PhoneChargeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone_number']
        amount = serializer.validated_data['amount']
        seller = request.user

        with transaction.atomic():
            # Lock the seller row
            seller_locked = Seller.objects.select_for_update().get(pk=seller.pk)

            # Ensure sufficient funds
            if seller_locked.balance < amount:
                return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

            # Lock phone number row
            phone_locked = PhoneNumber.objects.select_for_update().get(pk=phone.pk)

            # Debit seller
            seller_locked.balance = F('balance') - amount
            seller_locked.save(update_fields=['balance'])

            # Credit phone
            phone_locked.balance = F('balance') + amount
            phone_locked.save(update_fields=['balance'])

            # Log the transaction
            Transaction.objects.create(
                seller=seller_locked,
                amount=amount,
                transaction_type='debit',
                description=f"Charged phone {phone_locked.number}"
            )

        # Final response with fresh values
        seller.refresh_from_db()
        phone.refresh_from_db()
        return Response({
            "message": "Phone charged successfully.",
            "seller_balance": str(seller.balance),
            "phone_balance": str(phone.balance)
        }, status=status.HTTP_200_OK)
