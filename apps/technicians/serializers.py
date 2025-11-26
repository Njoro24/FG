from rest_framework import serializers
from .models import TechnicianAvailability, TechnicianLocation


class TechnicianAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianAvailability
        fields = '__all__'


class TechnicianLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianLocation
        fields = '__all__'
