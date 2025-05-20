from rest_framework import serializers
from .models import Seller

class SellerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = Seller
        fields = ['id', 'username', 'password', 'phone_number', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        seller   = Seller(**validated_data)
        seller.set_password(password)
        seller.save()
        return seller

class SellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ['id', 'username', 'phone_number', 'balance', 'created_at']
        read_only_fields = ['id', 'balance', 'created_at']
