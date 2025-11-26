from django.contrib import admin
from .models import TechnicianProfile, TechnicianAvailability, TechnicianLocation
from apps.accounts.email_service import send_verification_status_email


@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'verification_status', 'rating', 'completed_jobs_count', 'is_online']
    list_filter = ['verification_status', 'is_online']
    search_fields = ['user__email', 'phone']
    actions = ['approve_technician', 'reject_technician']
    
    def approve_technician(self, request, queryset):
        for profile in queryset:
            profile.verification_status = 'approved'
            profile.user.is_technician = True
            profile.user.save()
            profile.save()
            send_verification_status_email(profile.user.email, 'approved')
        self.message_user(request, f"{queryset.count()} technicians approved")
    approve_technician.short_description = "Approve selected technicians"
    
    def reject_technician(self, request, queryset):
        for profile in queryset:
            profile.verification_status = 'rejected'
            profile.save()
            send_verification_status_email(profile.user.email, 'rejected', profile.rejection_reason)
        self.message_user(request, f"{queryset.count()} technicians rejected")
    reject_technician.short_description = "Reject selected technicians"


@admin.register(TechnicianAvailability)
class TechnicianAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['technician', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available']
    search_fields = ['technician__email']


@admin.register(TechnicianLocation)
class TechnicianLocationAdmin(admin.ModelAdmin):
    list_display = ['technician', 'city', 'latitude', 'longitude', 'service_radius_km']
    search_fields = ['technician__email', 'city']
