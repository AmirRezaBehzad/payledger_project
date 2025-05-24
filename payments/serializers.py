from django.forms import ValidationError
from rest_framework import serializers
from .models import Transaction, CreditRequest, PhoneNumber, PhoneCharge
from .models import CreditRequest, Status
from rest_framework.fields import CurrentUserDefault, HiddenField

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
    # <-- DRF will populate this from request.user automatically
    seller = HiddenField(default=CurrentUserDefault())

    status = serializers.IntegerField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CreditRequest
        fields = ['id', 'seller', 'amount', 'status', 'created_at', 'approved_at']
        read_only_fields = ['status', 'approved_at']

class PhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ['id', 'number', 'name', 'created_at']

# class PhoneChargeSerializer(serializers.Serializer):
#     # seller       = serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all())
#     phone_number = serializers.PrimaryKeyRelatedField(queryset=PhoneNumber.objects.all())
#     amount       = serializers.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         min_value=0.01,               # ensures amount > 0
#         error_messages={'min_value': 'Charge amount must be greater than zero.'}
#     )

#     def validate(self, data):
#         """
#         Object-level validation: make sure the seller has enough balance.
#         """
#         seller = self.context['request'].user
#         amount = data['amount']
#         if seller.balance < amount:
#             raise serializers.ValidationError("Insufficient seller balance to perform this charge.")
#         return data

# serializers.py

# class PhoneChargeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PhoneCharge
#         fields = ['id', 'phone_number', 'amount', 'created_at']
#         read_only_fields = ['id','created_at']

#     # def create(self, validated_data):
#     #     charge = PhoneCharge.objects.create(**validated_data)
#     #     try:
#     #         charge.process_charge()
#     #         return charge
#     #     except ValidationError as e:
#     #         charge.delete()
#     #         raise serializers.ValidationError(str(e))
#     def create(self, validated_data):
#         # simply create — do NOT call process_charge here
#         return PhoneCharge.objects.create(
#             seller=self.context['request'].user,
#             **validated_data
#         )

class PhoneChargeSerializer(serializers.ModelSerializer):
    # DRF will put request.user here automatically,
    # and not include 'seller' in validated_data from the client.
    seller = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = PhoneCharge
        fields = ['id', 'seller', 'phone_number', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']
