from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer
from .otp_service import generate_otp, store_otp, verify_otp
from .email_service import send_otp_email, send_welcome_email
from .throttles import OTPRequestThrottle, OTPVerifyThrottle


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRequestThrottle])
def signup(request):
    """Register a new user and send OTP for verification"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate and send OTP
        otp = generate_otp()
        store_otp(user.email, otp)
        send_otp_email(user.email, otp)
        
        return Response({
            'message': 'Registration successful. Please verify your email with the OTP sent.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def technician_signup(request):
    """Register a new technician with KYC data"""
    import re
    from apps.technicians.models import TechnicianProfile, TechnicianLocation
    
    # Validate required fields
    required_fields = ['email', 'password', 'password2', 'first_name', 'last_name', 
                       'phone_number', 'id_number', 'profile_photo', 'id_front_photo', 
                       'id_back_photo', 'selfie_with_id']
    
    for field in required_fields:
        if not request.data.get(field):
            return Response({'error': f'{field} is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    password = request.data.get('password')
    if password != request.data.get('password2'):
        return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Password strength validation
    if len(password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[A-Z]', password):
        return Response({'error': 'Password must contain at least one uppercase letter'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[a-z]', password):
        return Response({'error': 'Password must contain at least one lowercase letter'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'\d', password):
        return Response({'error': 'Password must contain at least one number'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return Response({'error': 'Password must contain at least one special character (!@#$%^&*)'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if email exists
    email = request.data.get('email')
    existing_user = User.objects.filter(email=email).first()
    
    if existing_user:
        # Check if user has a technician profile already
        if hasattr(existing_user, 'technician_profile'):
            return Response({'error': 'A technician account with this email already exists. Please login instead.'}, status=status.HTTP_400_BAD_REQUEST)
        # User exists but no technician profile - delete and recreate
        existing_user.delete()
    
    try:
        # Create user
        user = User.objects.create_user(
            email=email,
            password=request.data.get('password'),
            full_name=f"{request.data.get('first_name')} {request.data.get('last_name')}",
            phone_number=request.data.get('phone_number'),
            is_technician=True,
            is_active=False  # Will be activated after OTP verification
        )
        user.first_name = request.data.get('first_name')
        user.last_name = request.data.get('last_name')
        user.save()
        
        # Create technician profile with KYC data
        profile = TechnicianProfile.objects.create(
            user=user,
            phone=request.data.get('phone_number'),
            skills=request.data.get('skills', []),
            bio=request.data.get('bio', ''),
            experience_years=int(request.data.get('experience_years', 0)),
            id_number=request.data.get('id_number'),
            profile_photo=request.data.get('profile_photo'),
            id_front_photo=request.data.get('id_front_photo'),
            id_back_photo=request.data.get('id_back_photo'),
            selfie_with_id=request.data.get('selfie_with_id'),
            kyc_status='pending',  # Submitted for review
            verification_status='pending'
        )
        
        # Create location if provided
        if request.data.get('latitude') and request.data.get('longitude'):
            TechnicianLocation.objects.create(
                technician=user,
                latitude=request.data.get('latitude'),
                longitude=request.data.get('longitude'),
                address=request.data.get('address', ''),
                city=request.data.get('address', '').split(',')[0] if request.data.get('address') else '',
                service_radius_km=int(request.data.get('service_radius', 10))
            )
        
        # Generate and send OTP
        otp = generate_otp()
        store_otp(user.email, otp)
        send_otp_email(user.email, otp)
        
        return Response({
            'message': 'Registration successful. Please verify your email. Your ID will be verified within 24-48 hours.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRequestThrottle])
def request_otp(request):
    """Request OTP for email verification"""
    email = request.data.get('email')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        otp = generate_otp()
        store_otp(email, otp)
        send_otp_email(email, otp)
        
        return Response({'message': 'OTP sent to your email'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPVerifyThrottle])
def verify_otp_view(request):
    """Verify OTP and activate user account"""
    email = request.data.get('email')
    otp = request.data.get('otp')
    
    if not email or not otp:
        return Response({'error': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if verify_otp(email, otp):
        try:
            user = User.objects.get(email=email)
            user.email_verified = True
            user.is_active = True
            user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Send welcome email
            send_welcome_email(user.email, user.full_name or user.email)
            
            return Response({
                'message': 'Email verified successfully',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login user and return JWT tokens"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists first
    try:
        user_exists = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({
            'error': 'No account found with this email. Please sign up first.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = authenticate(username=email, password=password)
    
    if user:
        if not user.email_verified:
            return Response({
                'error': 'Email not verified. Please verify your email first.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
    
    return Response({'error': 'Incorrect password. Please try again.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update current user profile"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({'error': 'Both old and new passwords are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    if not user.check_password(old_password):
        return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': 'Password changed successfully'})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_photo(request):
    """Update user profile photo"""
    profile_photo = request.data.get('profile_photo')
    
    if not profile_photo:
        return Response({'error': 'Profile photo URL is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    user.profile_photo = profile_photo
    user.save()
    
    return Response({
        'message': 'Profile photo updated',
        'profile_photo': user.profile_photo,
        'user': UserSerializer(user).data
    })
