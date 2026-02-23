from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer to handle user data conversion. 
    Includes custom fields for Resolv's social accountability features.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'reliability_score', 'upi_id', 'currency_preference']
        # Ensure password is not returned in API responses for security
        extra_kwargs = {
            'password': {'write_only': True},
            'reliability_score': {'read_only': True} # Score is managed by the system, not the user
        }

    def create(self, validated_data):
        """
        Overrides the create method to ensure passwords are correctly hashed.
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            upi_id=validated_data.get('upi_id', ''),
            currency_preference=validated_data.get('currency_preference', 'INR')
        )
        return user