from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet)
router.register(r'wallet', views.WalletViewSet, basename='wallet')
router.register(r'payouts', views.PayoutRequestViewSet)

urlpatterns = [
    path('initiate/', views.initiate_payment, name='initiate_payment'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('', include(router.urls)),
]
