from rest_framework import serializers
from .models import User
import re

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer to handle user data conversion. 
    Includes custom fields for Resolv's social accountability features.
    """
    class Meta:
        model = User
        # Added avatar_url so DRF allows it through validation
        fields = ['id', 'username', 'email', 'password', 'reliability_score', 'upi_id', 'currency_preference', 'avatar_url']
        
        extra_kwargs = {
            'password': {'write_only': True},
            'reliability_score': {'read_only': True} 
        }

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one symbol.")
        return value

    def create(self, validated_data):
        """
        Overrides the create method to ensure passwords are correctly hashed.
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            upi_id=validated_data.get('upi_id', ''),
            currency_preference=validated_data.get('currency_preference', 'INR'),
            avatar_url=validated_data.get('avatar_url', '')
        )
        return user
    
    def update(self, instance, validated_data):
        """
        Intercepts password updates to ensure they are hashed.
        """
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        
        return super().update(instance, validated_data)