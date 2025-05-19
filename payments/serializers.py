from rest_framework import serializers
from .models import Seller, Transaction, CreditRequest, PhoneNumber, Status

class SellerSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(
        max_length=15,
        min_length=10,
        required=True,
        help_text="Phone number should be between 10 and 15 characters."
    )

    def validate_phone_number(self, value):
        # Simple check: phone number should be digits only (you can enhance regex if needed)
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain digits only.")
        return value

    class Meta:
        model = Seller
        fields = ['id', 'phone_number', 'balance', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    transaction_type = serializers.ChoiceField(choices=['credit', 'debit'])
    
    class Meta:
        model = Transaction
        fields = ['id', 'seller', 'amount', 'transaction_type', 'timestamp', 'description']

    def validate(self, data):
        amount = data.get('amount')
        transaction_type = data.get('transaction_type')

        if transaction_type == 'debit' and amount <= 0:
            raise serializers.ValidationError("Debit amount must be positive.")

        if transaction_type == 'credit' and amount <= 0:
            raise serializers.ValidationError("Credit amount must be positive.")

        return data

class CreditRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditRequest
        fields = ['id', 'seller', 'amount', 'created_at', 'approved_at']
        read_only_fields = ['approved_at']

        def create(self, validated_data):
            # lookup your “pending” Status object
            pending = Status.objects.get(name='pending')
            validated_data['status'] = pending
            return super().create(validated_data)

class PhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ['id', 'number', 'name', 'created_at']

class PhoneChargeSerializer(serializers.Serializer):
    seller = serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all())
    phone_number = serializers.PrimaryKeyRelatedField(queryset=PhoneNumber.objects.all())
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
