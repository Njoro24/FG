from django.db import models
from django.conf import settings
from apps.accounts.models import User
from django.utils import timezone


class JobPosting(models.Model):
    """Jobs posted by customers for technicians to bid on"""
    STATUS_CHOICES = (
        ('open', 'Open for Bids'),
        ('in_review', 'Reviewing Bids'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    CATEGORY_CHOICES = (
        ('phone_repair', 'Phone Repairs'),
        ('laptop_repair', 'Laptop Repairs'),
        ('solar_systems', 'Solar Systems'),
        ('water_pumps', 'Water Pumps'),
        ('fridges', 'Fridges & Freezers'),
        ('cookers', 'Cookers & Ovens'),
        ('microwaves', 'Microwaves'),
        ('showers', 'Showers & Geysers'),
        ('tv_mounting', 'TV Mounting'),
        ('cctv', 'CCTV Installation'),
        ('electric_fence', 'Electric Fence'),
        ('appliances', 'Small Appliances'),
        ('movers', 'Movers & Relocation'),
        ('other', 'Other'),
    )
    
    URGENCY_CHOICES = (
        ('low', 'Not Urgent - Within a week'),
        ('medium', 'Soon - Within 2-3 days'),
        ('high', 'Urgent - Within 24 hours'),
        ('emergency', 'Emergency - ASAP'),
    )
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_postings')
    assigned_technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium')
    
    # Images of the problem
    images = models.JSONField(default=list)
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField()
    
    # Budget
    budget_min = models.DecimalField(max_digits=10, decimal_places=2)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Platform fee (15%)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    technician_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment - Multiple options, no cash for security
    PAYMENT_METHOD_CHOICES = (
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('stripe', 'Stripe (Card)'),
        ('paypal', 'PayPal'),
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    payment_status = models.CharField(max_length=20, default='pending')  # pending, paid, released
    
    # Scheduling
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Bid stats
    total_bids = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Job #{self.id} - {self.title}"
    
    def is_open(self):
        return self.status == 'open'
    
    def calculate_fees(self, amount):
        """Calculate platform fee (15%) and technician earnings"""
        from decimal import Decimal
        commission_rate = Decimal('0.15')  # 15% platform fee
        self.platform_fee = amount * commission_rate
        self.technician_earnings = amount - self.platform_fee
        return self.platform_fee, self.technician_earnings
    
    def accept_bid(self, bid):
        """Accept a bid and assign the technician"""
        self.assigned_technician = bid.technician
        self.final_price = bid.amount
        self.calculate_fees(bid.amount)
        self.status = 'assigned'
        self.save()
        
        # Update bid status
        bid.status = 'accepted'
        bid.save()
        
        # Reject other bids
        self.bids.exclude(id=bid.id).update(status='rejected')


class Bid(models.Model):
    """Bids from technicians on job postings"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='bids')
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(help_text="Why should the customer choose you?")
    estimated_duration = models.CharField(max_length=50, blank=True)  # e.g., "2-3 hours"
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['amount', '-created_at']
        unique_together = ['job', 'technician']  # One bid per technician per job
    
    def __str__(self):
        return f"Bid #{self.id} - KES {self.amount} by {self.technician.email}"


class Booking(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('enroute', 'En Route'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    CATEGORY_CHOICES = (
        ('phone_repair', 'Phone Repair'),
        ('laptop_repair', 'Laptop Repair'),
        ('tablet_repair', 'Tablet Repair'),
        ('computer_repair', 'Computer Repair'),
        ('solar_systems', 'Solar Systems'),
        ('water_pumps', 'Water Pumps'),
        ('fridges', 'Fridges & Freezers'),
        ('cookers', 'Cookers & Ovens'),
        ('microwaves', 'Microwaves'),
        ('showers', 'Showers & Geysers'),
        ('tv_mounting', 'TV Mounting'),
        ('cctv', 'CCTV Installation'),
        ('electric_fence', 'Electric Fence'),
        ('appliances', 'Small Appliances'),
        ('movers', 'Movers & Relocation'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_bookings')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='technician_bookings')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    images = models.JSONField(default=list)  # List of image URLs
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField()
    
    # Scheduling
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    technician_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment - Multiple options, no cash for security
    PAYMENT_METHOD_CHOICES = (
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('stripe', 'Stripe (Card)'),
        ('paypal', 'PayPal'),
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    payment_status = models.CharField(max_length=20, default='pending')  # pending, paid, failed
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Booking #{self.id} - {self.title}"
    
    def calculate_fees(self):
        """Calculate platform and technician fees based on cost"""
        if self.cost:
            commission_rate = getattr(settings, 'PLATFORM_COMMISSION_RATE', 0.15)
            self.platform_fee = self.cost * commission_rate
            self.technician_fee = self.cost - self.platform_fee
    
    def save(self, *args, **kwargs):
        if self.cost and not self.platform_fee:
            self.calculate_fees()
        super().save(*args, **kwargs)
