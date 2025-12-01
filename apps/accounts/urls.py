from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('signup/', views.signup, name='signup'),
    path('technician-signup/', views.technician_signup, name='technician_signup'),
    path('login/', views.login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # OTP
    path('request-otp/', views.request_otp, name='request_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/photo/', views.update_profile_photo, name='update_profile_photo'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Admin cleanup (temporary - remove after use)
    path('cleanup-user/', views.cleanup_user, name='cleanup_user'),
]
