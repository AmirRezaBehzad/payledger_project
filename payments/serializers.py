from rest_framework import serializers
from .models import Seller, Transaction, CreditRequest, PhoneNumber, Status

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
    status = serializers.IntegerField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CreditRequest
        # fields = ['id', 'seller', 'amount', 'status', 'created_at', 'approved_at']
        fields = ['id', 'amount', 'status', 'created_at', 'approved_at']
        read_only_fields = ['status', 'approved_at']

        def create(self, validated_data):
            seller = self.context['request'].user  # Automatically use the logged-in user
            return CreditRequest.objects.create(seller=seller, **validated_data)

class PhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ['id', 'number', 'name', 'created_at']

class PhoneChargeSerializer(serializers.Serializer):
    # seller       = serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all())
    phone_number = serializers.PrimaryKeyRelatedField(queryset=PhoneNumber.objects.all())
    amount       = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,               # ensures amount > 0
        error_messages={'min_value': 'Charge amount must be greater than zero.'}
    )

    def validate(self, data):
        """
        Object-level validation: make sure the seller has enough balance.
        """
        seller = self.context['request'].user
        amount = data['amount']
        if seller.balance < amount:
            raise serializers.ValidationError("Insufficient seller balance to perform this charge.")
        return data

