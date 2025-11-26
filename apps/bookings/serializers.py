from rest_framework import serializers
from .models import Booking
from apps.accounts.serializers import UserSerializer


class BookingSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    technician = UserSerializer(read_only=True)
    
    class Meta:
        model = Booking
        fields = '__all__'


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['technician', 'device_type', 'device_brand', 'device_model', 
                  'issue_description', 'scheduled_date', 'location_address']
