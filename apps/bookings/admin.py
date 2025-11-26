from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'technician', 'category', 'status', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['user__email', 'technician__email', 'title']
