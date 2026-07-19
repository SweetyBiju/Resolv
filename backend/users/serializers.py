from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Used ONLY for POST /auth/register/ — includes password."""

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'password', 'currency_preference']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        #  delegate to Django's configured validators, don't reimplement
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            currency_preference=validated_data.get('currency_preference', 'INR'),
        )


class UserProfileSerializer(serializers.ModelSerializer):
    """Used for GET /users/me/ — safe read-only public profile."""
    # annotated at view level, exposed here as read-only
    settlement_count = serializers.IntegerField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'email', 'reliability_score',
            'currency_preference', 'avatar_url', 'settlement_count',
            'date_joined'
        ]
        read_only_fields = fields  # This serializer is purely for reads


class UserUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /users/me/ — profile updates with password guard."""
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model  = User
        fields = ['username', 'currency_preference', 'upi_id',
                  'avatar_url', 'old_password', 'new_password']

    def validate(self, data):
        # password change requires current password
        if 'new_password' in data:
            if 'old_password' not in data:
                raise serializers.ValidationError(
                    {"old_password": "Current password is required to set a new one."}
                )
            if not self.instance.check_password(data['old_password']):
                raise serializers.ValidationError(
                    {"old_password": "Current password is incorrect."}
                )
            try:
                validate_password(data['new_password'], self.instance)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"new_password": list(e.messages)})
        return data


class PublicUserSerializer(serializers.ModelSerializer):
    """Used for other users' profiles, embedded in group responses."""
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_url', 'reliability_score']
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    """Used specifically for POST /users/change-password/"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        try:
            validate_password(value, user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user