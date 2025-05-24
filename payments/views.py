from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CreditRequest, PhoneCharge, Transaction
from rest_framework.permissions import IsAuthenticated
from .serializers import TransactionSerializer, CreditRequestSerializer, PhoneChargeSerializer
from django.core.exceptions import ValidationError

class TransactionCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Transaction.objects.all().order_by('-timestamp')

        if not request.user.is_staff:
            qs = qs.filter(seller=request.user)

        serializer = TransactionSerializer(qs, many=True)
        return Response(serializer.data)

class CreditRequestCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CreditRequest.objects.filter(seller=request.user).order_by('-created_at')
        serializer = CreditRequestSerializer(qs, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CreditRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(seller=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PhoneChargeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PhoneCharge.objects.filter(seller=request.user).order_by('-created_at')
        serializer = PhoneChargeSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PhoneChargeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        phone_charge = serializer.save(seller=request.user)

        try:
            phone_charge.process_charge()
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message":        "Phone charged successfully.",
            "seller_balance": str(phone_charge.seller.balance),
            "phone_balance":  str(phone_charge.phone_number.balance)
        }, status=status.HTTP_200_OK)