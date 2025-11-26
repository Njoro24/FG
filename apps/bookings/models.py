from django.db import models
from django.conf import settings
from apps.accounts.models import User


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
