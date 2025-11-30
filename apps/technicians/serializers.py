from rest_framework import serializers
from .models import TechnicianProfile, TechnicianAvailability, TechnicianLocation


class TechnicianProfileSerializer(serializers.ModelSerializer):
    """Public profile serializer - shown to customers"""
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    is_verified = serializers.SerializerMethodField()
    is_kyc_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'name', 'email', 'phone', 'skills', 'bio', 'experience_years',
            'profile_photo', 'verification_status', 'is_verified', 'is_kyc_verified',
            'rating', 'total_ratings', 'trust_score', 'completed_jobs_count',
            'is_online', 'is_active', 'created_at'
        ]
    
    def get_name(self, obj):
        return obj.user.full_name or obj.user.email.split('@')[0]
    
    def get_is_verified(self, obj):
        return obj.verification_status == 'approved'
    
    def get_is_kyc_verified(self, obj):
        return obj.kyc_status == 'approved'


class TechnicianDashboardSerializer(serializers.ModelSerializer):
    """Full profile for technician's own dashboard"""
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'user_id', 'name', 'email', 'phone', 'skills', 'bio', 'experience_years',
            'profile_photo', 'id_number',
            'id_front_photo', 'id_back_photo', 'selfie_with_id',
            'kyc_status', 'kyc_rejection_reason', 'kyc_submitted_at', 'kyc_verified_at',
            'verification_status', 'rejection_reason',
            'rating', 'total_ratings', 'trust_score',
            'wallet_balance', 'total_earnings', 'pending_earnings',
            'completed_jobs_count', 'cancelled_jobs_count', 'active_jobs_count',
            'is_online', 'is_active', 'is_available_for_jobs',
            'created_at', 'updated_at'
        ]
    
    def get_name(self, obj):
        return obj.user.full_name or obj.user.email.split('@')[0]


class KYCSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for KYC document submission"""
    class Meta:
        model = TechnicianProfile
        fields = ['id_number', 'id_front_photo', 'id_back_photo', 'selfie_with_id', 'profile_photo']
    
    def validate(self, data):
        # Ensure all required KYC fields are provided
        required_fields = ['id_number', 'id_front_photo', 'id_back_photo', 'selfie_with_id', 'profile_photo']
        missing = [f for f in required_fields if not data.get(f) and not getattr(self.instance, f, None)]
        
        if missing:
            raise serializers.ValidationError({
                'error': f'Missing required fields: {", ".join(missing)}'
            })
        return data


class TechnicianAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianAvailability
        fields = '__all__'


class TechnicianLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianLocation
        fields = '__all__'
