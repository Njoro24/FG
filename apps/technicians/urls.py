from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'availability', views.TechnicianAvailabilityViewSet)
router.register(r'location', views.TechnicianLocationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('top/', views.get_top_technicians, name='top_technicians'),
    path('by-skill/<str:skill>/', views.get_technicians_by_skill, name='technicians_by_skill'),
    path('profile/<int:technician_id>/', views.get_technician_profile, name='technician_profile'),
    
    # Technician's own profile & dashboard
    path('me/', views.get_my_technician_profile, name='my_technician_profile'),
    path('dashboard/', views.get_technician_dashboard, name='technician_dashboard'),
    
    # KYC endpoints
    path('kyc/submit/', views.submit_kyc, name='submit_kyc'),
    path('kyc/status/', views.get_kyc_status, name='kyc_status'),
    path('profile-photo/', views.update_profile_photo, name='update_profile_photo'),
]
