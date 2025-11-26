from rest_framework import serializers
from .models import Review
from apps.accounts.serializers import UserSerializer


class ReviewSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    technician = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = '__all__'


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['booking', 'technician', 'rating', 'comment']
