from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'bookings', views.BookingViewSet, basename='booking')
router.register(r'jobs', views.JobPostingViewSet, basename='job')
router.register(r'bids', views.BidViewSet, basename='bid')

urlpatterns = [
    path('', include(router.urls)),
]
