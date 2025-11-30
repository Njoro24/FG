from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet)
router.register(r'wallet', views.WalletViewSet, basename='wallet')
router.register(r'payouts-legacy', views.PayoutRequestViewSet)

urlpatterns = [
    # ============================================
    # JOB PAYMENT FLOW (Main Flow)
    # ============================================
    
    # Step 1: Client initiates payment
    path('job/initiate/', views.initiate_job_payment_view, name='initiate_job_payment'),
    
    # Step 2: Check payment status
    path('job/status/', views.check_payment_status, name='check_payment_status'),
    
    # Step 3: Release payment to technician (after job completion)
    path('job/release/', views.release_payment, name='release_payment'),
    
    # ============================================
    # M-PESA CALLBACKS
    # ============================================
    
    # STK Push callback (C2B - Client pays platform)
    path('mpesa/callback/', views.mpesa_stk_callback, name='mpesa_stk_callback'),
    
    # B2C callbacks (Platform pays technician)
    path('mpesa/b2c/result/', views.mpesa_b2c_result, name='mpesa_b2c_result'),
    path('mpesa/b2c/timeout/', views.mpesa_b2c_timeout, name='mpesa_b2c_timeout'),
    
    # ============================================
    # TECHNICIAN PAYOUTS
    # ============================================
    
    # Request payout
    path('payout/request/', views.request_payout, name='request_payout'),
    
    # Get payout history
    path('payout/history/', views.get_my_payouts, name='payout_history'),
    
    # ============================================
    # WALLET
    # ============================================
    
    # Get wallet balance
    path('wallet/balance/', views.get_wallet_balance, name='wallet_balance'),
    
    # Get wallet transactions
    path('wallet/transactions/', views.get_wallet_transactions, name='wallet_transactions'),
    
    # ============================================
    # PAYMENT HISTORY
    # ============================================
    
    # Client's payment history
    path('history/payments/', views.get_my_payments, name='my_payments'),
    
    # Technician's earnings history
    path('history/earnings/', views.get_my_earnings, name='my_earnings'),
    
    # ============================================
    # LEGACY ENDPOINTS (Backward Compatibility)
    # ============================================
    
    path('initiate/', views.initiate_payment, name='initiate_payment'),
    
    # Include router URLs
    path('', include(router.urls)),
]
