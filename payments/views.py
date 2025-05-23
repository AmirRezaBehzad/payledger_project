from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Seller, Transaction, PhoneNumber
from rest_framework.permissions import IsAuthenticated
from .serializers import TransactionSerializer, CreditRequestSerializer, PhoneChargeSerializer
from django.db.models import F
from django.core.exceptions import ValidationError

class TransactionCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        seller  = serializer.validated_data['seller']
        amount  = serializer.validated_data['amount']
        ttype   = serializer.validated_data['transaction_type']
        desc    = serializer.validated_data.get('description', '')

        try:
            txn = Transaction.create_transaction(
                seller     = seller,
                amount     = amount,
                ttype      = ttype,
                description=desc
            )
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        out = TransactionSerializer(txn)
        return Response(out.data, status=status.HTTP_201_CREATED)

class CreditRequestCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # serializer = CreditRequestSerializer(data=request.data)
        # after
        serializer = CreditRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(seller=request.user)   # ✅ Inject authenticated user as seller
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PhoneChargeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PhoneChargeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        phone_charge = serializer.save(seller=request.user)

        try:
            phone_charge.process_charge()
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # reload to get updated balances
        phone_charge.seller.refresh_from_db()
        phone_charge.phone_number.refresh_from_db()

        return Response({
            "message":        "Phone charged successfully.",
            "seller_balance": str(phone_charge.seller.balance),
            "phone_balance":  str(phone_charge.phone_number.balance)
        }, status=status.HTTP_200_OK)