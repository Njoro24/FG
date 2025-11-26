from django.db import models
from apps.accounts.models import User
from math import radians, cos, sin, asin, sqrt


class TechnicianProfile(models.Model):
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='technician_profile')
    phone = models.CharField(max_length=15)
    skills = models.JSONField(default=list)  # ['phone_repair', 'laptop_repair', 'tablet_repair']
    profile_photo = models.URLField(blank=True)
    id_front = models.URLField(blank=True)
    id_back = models.URLField(blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    rejection_reason = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    completed_jobs_count = models.IntegerField(default=0)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Technician: {self.user.email}"


class TechnicianLocation(models.Model):
    technician = models.OneToOneField(User, on_delete=models.CASCADE, related_name='location')
    address = models.TextField()
    city = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    service_radius_km = models.IntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.technician.email} - {self.city}"
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula (in km)"""
        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km
    
    def is_within_service_area(self, lat, lng):
        """Check if a location is within technician's service radius"""
        distance = self.calculate_distance(self.latitude, self.longitude, lat, lng)
        return distance <= self.service_radius_km


class TechnicianAvailability(models.Model):
    DAYS_OF_WEEK = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )
    
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['technician', 'day_of_week']
    
    def __str__(self):
        return f"{self.technician.email} - {self.day_of_week}"
