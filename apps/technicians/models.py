from django.db import models
from apps.accounts.models import User
from math import radians, cos, sin, asin, sqrt
from decimal import Decimal


class Company(models.Model):
    """Company/Business registration for service providers"""
    VERIFICATION_STATUS = (
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    COMPANY_TYPE = (
        ('sole_proprietor', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('limited', 'Limited Company'),
        ('other', 'Other'),
    )
    
    # Owner/Admin
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_companies')
    
    # Company Details
    name = models.CharField(max_length=255)
    company_type = models.CharField(max_length=20, choices=COMPANY_TYPE, default='sole_proprietor')
    registration_number = models.CharField(max_length=50, blank=True)  # Business registration number
    kra_pin = models.CharField(max_length=20, blank=True)  # KRA PIN for Kenya
    
    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    website = models.URLField(blank=True)
    
    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    
    # Services offered
    services = models.JSONField(default=list)  # e.g., ['laptop_repair', 'solar_systems', 'cctv']
    description = models.TextField(blank=True)
    
    # Branding
    logo = models.URLField(blank=True)
    
    # Verification Documents
    business_certificate = models.URLField(blank=True)  # Certificate of registration
    kra_certificate = models.URLField(blank=True)  # KRA PIN certificate
    business_permit = models.URLField(blank=True)  # County business permit
    
    # Verification Status
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='not_submitted')
    rejection_reason = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Commission rate (20% for companies vs 15% for individuals)
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0.20)
    
    # Stats
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_ratings = models.IntegerField(default=0)
    completed_jobs_count = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Companies"
    
    def __str__(self):
        return f"{self.name} ({self.company_type})"
    
    def is_verified(self):
        return self.verification_status == 'approved'
    
    def get_commission_rate(self):
        """Companies pay 20% commission"""
        return self.commission_rate


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
    
    ACCOUNT_TYPE = (
        ('individual', 'Individual'),
        ('company', 'Company'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='technician_profile')
    
    # Account type - individual or company
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE, default='individual')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='technicians')
    
    phone = models.CharField(max_length=15)
    skills = models.JSONField(default=list)
    bio = models.TextField(blank=True)
    experience_years = models.IntegerField(default=0)
    
    # Profile Photo (REQUIRED for security)
    # Using TextField to support base64 encoded images or URLs
    profile_photo = models.TextField(blank=True)
    
    # KYC Documents
    id_number = models.CharField(max_length=20, blank=True)
    # Using TextField to support base64 encoded images or URLs
    id_front_photo = models.TextField(blank=True)  # Front of ID card
    id_back_photo = models.TextField(blank=True)   # Back of ID card
    selfie_with_id = models.TextField(blank=True)  # Selfie holding ID for verification
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
        # For company accounts, check company verification
        if self.account_type == 'company' and self.company:
            return (
                self.is_active and 
                self.is_available_for_jobs and 
                self.company.verification_status == 'approved' and
                self.profile_photo
            )
        # For individual accounts, check KYC
        return (
            self.is_active and 
            self.is_available_for_jobs and 
            self.kyc_status == 'approved' and
            self.profile_photo
        )
    
    def get_commission_rate(self):
        """Get commission rate - 20% for companies, 15% for individuals"""
        if self.account_type == 'company' and self.company:
            return self.company.commission_rate
        return Decimal('0.15')  # 15% for individuals
    
    def __str__(self):
        if self.account_type == 'company' and self.company:
            return f"Technician: {self.user.email} ({self.company.name})"
        return f"Technician: {self.user.email}"


class TechnicianLocation(models.Model):
    """Technician location with live tracking support"""
    technician = models.OneToOneField(User, on_delete=models.CASCADE, related_name='location')
    address = models.TextField()
    city = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    service_radius_km = models.IntegerField(default=10)
    
    # Live tracking
    is_live = models.BooleanField(default=False)  # Is technician sharing live location?
    heading = models.FloatField(null=True, blank=True)  # Direction in degrees
    speed = models.FloatField(null=True, blank=True)  # Speed in km/h
    accuracy = models.FloatField(null=True, blank=True)  # GPS accuracy in meters
    
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
