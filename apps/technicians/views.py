from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import TechnicianProfile, TechnicianAvailability, TechnicianLocation, Company
from .serializers import (
    TechnicianProfileSerializer,
    TechnicianAvailabilitySerializer,
    TechnicianLocationSerializer,
    TechnicianDashboardSerializer,
    KYCSubmissionSerializer,
    CompanySerializer,
    CompanyRegistrationSerializer,
    CompanyVerificationSerializer,
    LiveLocationUpdateSerializer
)
from apps.accounts.permissions import IsTechnician


@api_view(['GET'])
@permission_classes([AllowAny])
def get_top_technicians(request):
    """Get top-rated verified technicians"""
    technicians = TechnicianProfile.objects.filter(
        verification_status='approved',
        is_active=True,
        trust_score__gte=0,
        kyc_status='approved'
    ).order_by('-rating', '-trust_score', '-completed_jobs_count')[:20]
    
    serializer = TechnicianProfileSerializer(technicians, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_technicians_by_skill(request, skill):
    """Get verified technicians by skill"""
    technicians = TechnicianProfile.objects.filter(
        verification_status='approved',
        is_active=True,
        trust_score__gte=0,
        kyc_status='approved',
        skills__contains=[skill]
    ).order_by('-rating', '-trust_score')[:10]
    
    serializer = TechnicianProfileSerializer(technicians, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_technician_profile(request, technician_id):
    """Get detailed technician profile"""
    try:
        technician = TechnicianProfile.objects.get(id=technician_id, is_active=True)
        serializer = TechnicianProfileSerializer(technician, context={'request': request})
        return Response(serializer.data)
    except TechnicianProfile.DoesNotExist:
        return Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_technician_profile(request):
    """Get current technician's own profile"""
    try:
        profile = TechnicianProfile.objects.get(user=request.user)
        serializer = TechnicianDashboardSerializer(profile, context={'request': request})
        return Response(serializer.data)
    except TechnicianProfile.DoesNotExist:
        return Response({'error': 'Technician profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_kyc(request):
    """Submit KYC documents for verification"""
    try:
        profile = TechnicianProfile.objects.get(user=request.user)
    except TechnicianProfile.DoesNotExist:
        return Response({'error': 'Technician profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if profile.kyc_status == 'approved':
        return Response({'error': 'KYC already approved'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = KYCSubmissionSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        profile = serializer.save()
        profile.kyc_status = 'pending'
        profile.kyc_submitted_at = timezone.now()
        profile.save()
        return Response({
            'message': 'KYC documents submitted successfully. Verification usually takes 24-48 hours.',
            'kyc_status': profile.kyc_status
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_kyc_status(request):
    """Get KYC verification status"""
    try:
        profile = TechnicianProfile.objects.get(user=request.user)
        return Response({
            'kyc_status': profile.kyc_status,
            'kyc_rejection_reason': profile.kyc_rejection_reason,
            'kyc_submitted_at': profile.kyc_submitted_at,
            'kyc_verified_at': profile.kyc_verified_at,
            'has_profile_photo': bool(profile.profile_photo),
            'has_id_front': bool(profile.id_front_photo),
            'has_id_back': bool(profile.id_back_photo),
            'has_selfie': bool(profile.selfie_with_id)
        })
    except TechnicianProfile.DoesNotExist:
        return Response({'error': 'Technician profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_photo(request):
    """Update technician profile photo"""
    try:
        profile = TechnicianProfile.objects.get(user=request.user)
    except TechnicianProfile.DoesNotExist:
        return Response({'error': 'Technician profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    profile_photo = request.data.get('profile_photo')
    if not profile_photo:
        return Response({'error': 'Profile photo URL is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile.profile_photo = profile_photo
    profile.save()
    return Response({'message': 'Profile photo updated', 'profile_photo': profile.profile_photo})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_technician_dashboard(request):
    """Get technician dashboard data"""
    try:
        profile = TechnicianProfile.objects.get(user=request.user)
    except TechnicianProfile.DoesNotExist:
        return Response({'error': 'Technician profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get recent jobs
    from apps.bookings.models import Booking, JobPosting, Bid
    
    active_jobs = Booking.objects.filter(
        technician=request.user,
        status__in=['accepted', 'enroute', 'in_progress']
    ).count()
    
    pending_bids = Bid.objects.filter(
        technician=request.user,
        status='pending'
    ).count()
    
    accepted_bids = Bid.objects.filter(
        technician=request.user,
        status='accepted'
    ).count()
    
    return Response({
        'profile': TechnicianDashboardSerializer(profile, context={'request': request}).data,
        'stats': {
            'active_jobs': active_jobs,
            'pending_bids': pending_bids,
            'accepted_bids': accepted_bids,
            'completed_jobs': profile.completed_jobs_count,
            'wallet_balance': float(profile.wallet_balance),
            'total_earnings': float(profile.total_earnings),
            'pending_earnings': float(profile.pending_earnings),
            'rating': float(profile.rating),
            'total_ratings': profile.total_ratings,
            'trust_score': profile.trust_score
        },
        'kyc': {
            'status': profile.kyc_status,
            'is_complete': profile.is_kyc_complete(),
            'can_accept_jobs': profile.can_accept_jobs()
        }
    })


class TechnicianAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = TechnicianAvailability.objects.all()
    serializer_class = TechnicianAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsTechnician]
    
    def get_queryset(self):
        return TechnicianAvailability.objects.filter(technician=self.request.user)


class TechnicianLocationViewSet(viewsets.ModelViewSet):
    queryset = TechnicianLocation.objects.all()
    serializer_class = TechnicianLocationSerializer
    permission_classes = [IsAuthenticated, IsTechnician]
    
    def get_queryset(self):
        return TechnicianLocation.objects.filter(technician=self.request.user)


# ============================================
# COMPANY ENDPOINTS
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_company(request):
    """Register a new company"""
    serializer = CompanyRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        company = serializer.save(owner=request.user)
        company.verification_status = 'pending'
        company.save()
        
        # Update technician profile to company type
        try:
            profile = TechnicianProfile.objects.get(user=request.user)
            profile.account_type = 'company'
            profile.company = company
            profile.save()
        except TechnicianProfile.DoesNotExist:
            # Create technician profile if doesn't exist
            TechnicianProfile.objects.create(
                user=request.user,
                account_type='company',
                company=company,
                phone=company.phone,
                skills=company.services
            )
            request.user.is_technician = True
            request.user.save()
        
        return Response({
            'message': 'Company registered successfully. Verification usually takes 24-48 hours.',
            'company': CompanySerializer(company).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_company(request):
    """Get current user's company"""
    try:
        company = Company.objects.get(owner=request.user)
        return Response(CompanySerializer(company).data)
    except Company.DoesNotExist:
        return Response({'error': 'No company found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_company(request):
    """Update company details"""
    try:
        company = Company.objects.get(owner=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'No company found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CompanyRegistrationSerializer(company, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(CompanySerializer(company).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_company_verification(request):
    """Submit company verification documents"""
    try:
        company = Company.objects.get(owner=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'No company found'}, status=status.HTTP_404_NOT_FOUND)
    
    if company.verification_status == 'approved':
        return Response({'error': 'Company already verified'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = CompanyVerificationSerializer(company, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        company.verification_status = 'pending'
        company.save()
        return Response({
            'message': 'Verification documents submitted. Review takes 24-48 hours.',
            'verification_status': company.verification_status
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_verified_companies(request):
    """Get list of verified companies"""
    companies = Company.objects.filter(
        verification_status='approved',
        is_active=True
    ).order_by('-rating', '-completed_jobs_count')[:20]
    
    return Response(CompanySerializer(companies, many=True).data)


# ============================================
# LIVE LOCATION ENDPOINTS
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_live_location(request):
    """Update technician's live location"""
    serializer = LiveLocationUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    location, created = TechnicianLocation.objects.update_or_create(
        technician=request.user,
        defaults={
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'heading': data.get('heading'),
            'speed': data.get('speed'),
            'accuracy': data.get('accuracy'),
            'is_live': data.get('is_live', True),
            'address': request.data.get('address', ''),
            'city': request.data.get('city', ''),
        }
    )
    
    return Response({
        'message': 'Location updated',
        'location': TechnicianLocationSerializer(location).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_live_location(request):
    """Stop sharing live location"""
    try:
        location = TechnicianLocation.objects.get(technician=request.user)
        location.is_live = False
        location.save()
        return Response({'message': 'Live location stopped'})
    except TechnicianLocation.DoesNotExist:
        return Response({'error': 'No location found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_technician_live_location(request, technician_id):
    """Get a technician's live location (for customers tracking their technician)"""
    try:
        location = TechnicianLocation.objects.get(
            technician_id=technician_id,
            is_live=True
        )
        return Response({
            'latitude': str(location.latitude),
            'longitude': str(location.longitude),
            'heading': location.heading,
            'speed': location.speed,
            'accuracy': location.accuracy,
            'last_updated': location.last_updated
        })
    except TechnicianLocation.DoesNotExist:
        return Response({'error': 'Technician location not available'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_nearby_technicians(request):
    """Get technicians near a location"""
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = request.query_params.get('radius', 10)  # Default 10km
    skill = request.query_params.get('skill')
    
    if not lat or not lng:
        return Response({'error': 'lat and lng are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        lat = float(lat)
        lng = float(lng)
        radius = float(radius)
    except ValueError:
        return Response({'error': 'Invalid coordinates'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get all active technicians with locations
    technicians = TechnicianProfile.objects.filter(
        is_active=True,
        is_available_for_jobs=True
    ).select_related('user')
    
    # Filter by skill if provided
    if skill:
        technicians = technicians.filter(skills__contains=[skill])
    
    # Filter by verified status
    technicians = technicians.filter(
        Q(kyc_status='approved') | Q(account_type='company', company__verification_status='approved')
    )
    
    nearby = []
    for tech in technicians:
        try:
            location = tech.user.location
            distance = TechnicianLocation.calculate_distance(lat, lng, location.latitude, location.longitude)
            if distance <= radius:
                tech_data = TechnicianProfileSerializer(tech).data
                tech_data['distance_km'] = round(distance, 2)
                tech_data['location'] = {
                    'latitude': str(location.latitude),
                    'longitude': str(location.longitude),
                    'is_live': location.is_live
                }
                nearby.append(tech_data)
        except TechnicianLocation.DoesNotExist:
            continue
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance_km'])
    
    return Response(nearby[:20])
