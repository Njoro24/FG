from django.db import models
from apps.accounts.models import User
from math import radians, cos, sin, asin, sqrt
from decimal import Decimal


class TechnicianProfile(models.Model):
    VERIFICATION_STATUS = (
        ('unverified', 'Unverified'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    KYC_STATUS = (
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='technician_profile')
    phone = models.CharField(max_length=15)
    skills = models.JSONField(default=list)
    bio = models.TextField(blank=True)
    experience_years = models.IntegerField(default=0)
    
    # Profile Photo (REQUIRED for security)
    profile_photo = models.URLField(blank=True)
    
    # KYC Documents
    id_number = models.CharField(max_length=20, blank=True)
    id_front_photo = models.URLField(blank=True)  # Front of ID card
    id_back_photo = models.URLField(blank=True)   # Back of ID card
    selfie_with_id = models.URLField(blank=True)  # Selfie holding ID for verification
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS, default='not_submitted')
    kyc_rejection_reason = models.TextField(blank=True)
    kyc_submitted_at = models.DateTimeField(null=True, blank=True)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Verification & Trust
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='unverified')
    rejection_reason = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_ratings = models.IntegerField(default=0)
    trust_score = models.IntegerField(default=5)
    
    # Wallet & Earnings
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pending_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Job Stats
    completed_jobs_count = models.IntegerField(default=0)
    cancelled_jobs_count = models.IntegerField(default=0)
    active_jobs_count = models.IntegerField(default=0)
    
    # Status
    is_online = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_available_for_jobs = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def update_trust_score(self, rating_value):
        """Update trust score based on rating (1-5 stars)"""
        if rating_value >= 4:
            self.trust_score += 5
        elif rating_value <= 2:
            self.trust_score -= 5
        
        if self.trust_score <= -10:
            self.is_active = False
            self.user.is_active = False
            self.user.save()
        
        self.save()
    
    def add_rating(self, rating_value):
        """Add a new rating and update average"""
        total = float(self.rating) * self.total_ratings
        self.total_ratings += 1
        self.rating = Decimal((total + rating_value) / self.total_ratings)
        self.update_trust_score(rating_value)
    
    def add_earnings(self, amount):
        """Add earnings to wallet"""
        self.wallet_balance += Decimal(amount)
        self.total_earnings += Decimal(amount)
        self.save()
    
    def is_kyc_complete(self):
        """Check if KYC is complete and approved"""
        return self.kyc_status == 'approved'
    
    def can_accept_jobs(self):
        """Check if technician can accept jobs"""
        return (
            self.is_active and 
            self.is_available_for_jobs and 
            self.kyc_status == 'approved' and
            self.profile_photo
        )
    
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
