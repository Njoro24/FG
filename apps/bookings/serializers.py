from rest_framework import serializers
from .models import Booking, JobPosting, Bid
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
        fields = ['technician', 'title', 'description', 'category',
                  'latitude', 'longitude', 'address', 'scheduled_time',
                  'payment_method', 'cost']


# Job Posting Serializers
class JobPostingSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    assigned_technician = UserSerializer(read_only=True)
    bids_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPosting
        fields = '__all__'
    
    def get_bids_count(self, obj):
        return obj.bids.count()


class JobPostingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = ['title', 'description', 'category', 'urgency',
                  'latitude', 'longitude', 'address',
                  'budget_min', 'budget_max', 'preferred_date', 'preferred_time', 'images']


class JobPostingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing jobs"""
    customer_name = serializers.SerializerMethodField()
    bids_count = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPosting
        fields = ['id', 'title', 'category', 'urgency', 'address',
                  'budget_min', 'budget_max', 'status', 'customer_name',
                  'bids_count', 'time_ago', 'created_at', 'latitude', 'longitude']
    
    def get_customer_name(self, obj):
        return obj.customer.full_name or obj.customer.email.split('@')[0]
    
    def get_bids_count(self, obj):
        return obj.bids.count()
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        diff = timezone.now() - obj.created_at
        if diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f"{mins} min ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hr ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days > 1 else ''} ago"


# Bid Serializers
class BidSerializer(serializers.ModelSerializer):
    technician = UserSerializer(read_only=True)
    technician_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = Bid
        fields = '__all__'
    
    def get_technician_profile(self, obj):
        try:
            profile = obj.technician.technician_profile
            return {
                'rating': float(profile.rating),
                'total_ratings': profile.total_ratings,
                'completed_jobs': profile.completed_jobs_count,
                'trust_score': profile.trust_score,
                'profile_photo': profile.profile_photo,
                'kyc_verified': profile.kyc_status == 'approved'
            }
        except:
            return None


class BidCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ['job', 'amount', 'message', 'estimated_duration']
    
    def validate(self, data):
        job = data.get('job')
        if job.status != 'open':
            raise serializers.ValidationError("This job is no longer accepting bids")
        
        # Check if technician already bid
        request = self.context.get('request')
        if request and Bid.objects.filter(job=job, technician=request.user).exists():
            raise serializers.ValidationError("You have already placed a bid on this job")
        
        return data


class BidListSerializer(serializers.ModelSerializer):
    """For technicians to see their bids"""
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_status = serializers.CharField(source='job.status', read_only=True)
    
    class Meta:
        model = Bid
        fields = ['id', 'job', 'job_title', 'job_status', 'amount', 
                  'message', 'status', 'created_at']
