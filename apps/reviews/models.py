from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User
from apps.bookings.models import Booking


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['booking', 'customer']
    
    def __str__(self):
        return f"Review by {self.customer.username} for {self.technician.username} - {self.rating}/5"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_technician_rating()
    
    def update_technician_rating(self):
        """Update technician's average rating."""
        from django.db.models import Avg, Count
        
        stats = Review.objects.filter(technician=self.technician).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        profile = self.technician.technician_profile
        profile.rating = stats['avg_rating'] or 0
        profile.total_reviews = stats['total_reviews'] or 0
        profile.save()
