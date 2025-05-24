from django.forms import ValidationError
from rest_framework import serializers
from .models import Transaction, CreditRequest, PhoneNumber, PhoneCharge
from .models import CreditRequest, Status
from rest_framework.fields import CurrentUserDefault, HiddenField

class TransactionSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
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

    # <-- Automatically set to the current authenticated user (CurrentUserDefault) on creation.
    seller = HiddenField(default=CurrentUserDefault())

    status = serializers.IntegerField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CreditRequest
        fields = ['id', 'seller', 'amount', 'status', 'created_at', 'approved_at']
        read_only_fields = ['id', 'status', 'created_at', 'approved_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

class PhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ['id', 'number', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

class PhoneChargeSerializer(serializers.ModelSerializer):

    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Charge amount must be greater than zero.")
        return value

    class Meta:
        model = PhoneCharge
        fields = ['id', 'seller', 'phone_number', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']
