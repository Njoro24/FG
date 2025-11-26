from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'first_name', 'last_name', 'phone_number', 
                  'is_technician', 'email_verified', 'created_at']
        read_only_fields = ['id', 'created_at', 'email_verified']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Split full_name into first_name and last_name if available
        if instance.full_name:
            parts = instance.full_name.split(' ', 1)
            data['first_name'] = parts[0] if parts else ''
            data['last_name'] = parts[1] if len(parts) > 1 else ''
        else:
            data['first_name'] = getattr(instance, 'first_name', '')
            data['last_name'] = getattr(instance, 'last_name', '')
        return data
    
    def update(self, instance, validated_data):
        # Handle first_name and last_name if provided
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        
        if first_name is not None or last_name is not None:
            # Get current values if not provided
            current_parts = instance.full_name.split(' ', 1) if instance.full_name else ['', '']
            fn = first_name if first_name is not None else (current_parts[0] if current_parts else '')
            ln = last_name if last_name is not None else (current_parts[1] if len(current_parts) > 1 else '')
            
            validated_data['full_name'] = f"{fn} {ln}".strip()
            instance.first_name = fn
            instance.last_name = ln
        
        return super().update(instance, validated_data)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'full_name', 'first_name', 'last_name', 'phone_number', 'password', 'password2']
    
    def validate(self, data):
        password = data.get('password')
        password2 = data.get('password2')
        
        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password2')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        # Create full_name from first_name and last_name if not provided
        if not validated_data.get('full_name'):
            validated_data['full_name'] = f"{first_name} {last_name}".strip()
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            is_active=False  # Will be activated after OTP verification
        )
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        return user
