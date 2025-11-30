from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from .models import TechnicianProfile, TechnicianAvailability, TechnicianLocation
from .serializers import (
    TechnicianProfileSerializer,
    TechnicianAvailabilitySerializer,
    TechnicianLocationSerializer,
    TechnicianDashboardSerializer,
    KYCSubmissionSerializer
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
