from rest_framework import serializers
from .models import TechnicianProfile, TechnicianAvailability, TechnicianLocation, Company


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for company details"""
    owner_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'company_type', 'registration_number', 'kra_pin',
            'email', 'phone', 'website', 'address', 'city',
            'services', 'description', 'logo',
            'verification_status', 'is_verified', 'commission_rate',
            'rating', 'total_ratings', 'completed_jobs_count',
            'is_active', 'owner_name', 'created_at'
        ]
        read_only_fields = ['owner', 'verification_status', 'commission_rate', 'rating', 
                           'total_ratings', 'completed_jobs_count', 'verified_at']
    
    def get_owner_name(self, obj):
        return obj.owner.full_name or obj.owner.email
    
    def get_is_verified(self, obj):
        return obj.verification_status == 'approved'


class CompanyRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for company registration"""
    class Meta:
        model = Company
        fields = [
            'name', 'company_type', 'registration_number', 'kra_pin',
            'email', 'phone', 'website', 'address', 'city',
            'services', 'description', 'logo',
            'business_certificate', 'kra_certificate', 'business_permit'
        ]
    
    def validate(self, data):
        # Require at least business certificate for verification
        if not data.get('business_certificate'):
            raise serializers.ValidationError({
                'business_certificate': 'Business registration certificate is required'
            })
        return data


class CompanyVerificationSerializer(serializers.ModelSerializer):
    """Serializer for company verification documents"""
    class Meta:
        model = Company
        fields = ['business_certificate', 'kra_certificate', 'business_permit']


class TechnicianProfileSerializer(serializers.ModelSerializer):
    """Public profile serializer - shown to customers"""
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    is_verified = serializers.SerializerMethodField()
    is_kyc_verified = serializers.SerializerMethodField()
    company_info = serializers.SerializerMethodField()
    commission_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'name', 'email', 'phone', 'skills', 'bio', 'experience_years',
            'profile_photo', 'account_type', 'company_info', 'commission_rate',
            'verification_status', 'is_verified', 'is_kyc_verified',
            'rating', 'total_ratings', 'trust_score', 'completed_jobs_count',
            'is_online', 'is_active', 'created_at'
        ]
    
    def get_name(self, obj):
        if obj.account_type == 'company' and obj.company:
            return obj.company.name
        return obj.user.full_name or obj.user.email.split('@')[0]
    
    def get_is_verified(self, obj):
        if obj.account_type == 'company' and obj.company:
            return obj.company.verification_status == 'approved'
        return obj.verification_status == 'approved'
    
    def get_is_kyc_verified(self, obj):
        if obj.account_type == 'company' and obj.company:
            return obj.company.verification_status == 'approved'
        return obj.kyc_status == 'approved'
    
    def get_company_info(self, obj):
        if obj.company:
            return {
                'id': obj.company.id,
                'name': obj.company.name,
                'logo': obj.company.logo,
                'verified': obj.company.verification_status == 'approved'
            }
        return None
    
    def get_commission_rate(self, obj):
        return str(obj.get_commission_rate())


class TechnicianDashboardSerializer(serializers.ModelSerializer):
    """Full profile for technician's own dashboard"""
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    company_info = serializers.SerializerMethodField()
    commission_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'user_id', 'name', 'email', 'phone', 'skills', 'bio', 'experience_years',
            'profile_photo', 'account_type', 'company_info', 'commission_rate', 'id_number',
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
        if obj.account_type == 'company' and obj.company:
            return obj.company.name
        return obj.user.full_name or obj.user.email.split('@')[0]
    
    def get_company_info(self, obj):
        if obj.company:
            return CompanySerializer(obj.company).data
        return None
    
    def get_commission_rate(self, obj):
        return str(obj.get_commission_rate())


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


class LiveLocationUpdateSerializer(serializers.Serializer):
    """Serializer for live location updates"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    heading = serializers.FloatField(required=False, allow_null=True)
    speed = serializers.FloatField(required=False, allow_null=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    is_live = serializers.BooleanField(default=True)
