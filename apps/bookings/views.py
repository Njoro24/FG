from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from .models import Booking, JobPosting, Bid
from .serializers import (
    BookingSerializer, BookingCreateSerializer,
    JobPostingSerializer, JobPostingCreateSerializer, JobPostingListSerializer,
    BidSerializer, BidCreateSerializer, BidListSerializer
)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_technician:
            return Booking.objects.filter(technician=user)
        return Booking.objects.filter(user=user)
    
    def create(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        if serializer.is_valid():
            booking = serializer.save(user=request.user)
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        if booking.technician != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        booking.status = 'accepted'
        booking.save()
        return Response(BookingSerializer(booking).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()
        if booking.technician != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        booking.status = 'completed'
        booking.save()
        return Response(BookingSerializer(booking).data)


class JobPostingViewSet(viewsets.ModelViewSet):
    """ViewSet for job postings - customers post, technicians bid"""
    queryset = JobPosting.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JobPostingCreateSerializer
        if self.action == 'list':
            return JobPostingListSerializer
        return JobPostingSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = JobPosting.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # For technicians - show open jobs they can bid on
        if self.request.query_params.get('available') == 'true':
            queryset = queryset.filter(status='open')
        
        # For customers - show their own jobs
        if self.request.query_params.get('my_jobs') == 'true':
            queryset = queryset.filter(customer=user)
        
        return queryset.order_by('-created_at')
    
    def create(self, request):
        """Customer creates a job posting"""
        serializer = JobPostingCreateSerializer(data=request.data)
        if serializer.is_valid():
            job = serializer.save(customer=request.user)
            return Response(JobPostingSerializer(job).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def bids(self, request, pk=None):
        """Get all bids for a job (customer only)"""
        job = self.get_object()
        if job.customer != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        bids = job.bids.all().order_by('amount')
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept_bid(self, request, pk=None):
        """Customer accepts a bid"""
        job = self.get_object()
        if job.customer != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        bid_id = request.data.get('bid_id')
        try:
            bid = Bid.objects.get(id=bid_id, job=job)
            job.accept_bid(bid)
            return Response({'message': 'Bid accepted', 'job': JobPostingSerializer(job).data})
        except Bid.DoesNotExist:
            return Response({'error': 'Bid not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a job posting"""
        job = self.get_object()
        if job.customer != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if job.status in ['completed', 'in_progress']:
            return Response({'error': 'Cannot cancel job in progress or completed'}, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = 'cancelled'
        job.save()
        return Response({'message': 'Job cancelled'})
    
    @action(detail=True, methods=['post'])
    def start_job(self, request, pk=None):
        """Technician starts working on the job"""
        job = self.get_object()
        if job.assigned_technician != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if job.status != 'assigned':
            return Response({'error': 'Job must be assigned before starting'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if payment has been made
        if job.payment_status != 'paid' and not hasattr(job, 'job_payment'):
            return Response({'error': 'Payment must be made before starting the job'}, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = 'in_progress'
        job.save()
        return Response({'message': 'Job started', 'job': JobPostingSerializer(job).data})
    
    @action(detail=True, methods=['post'])
    def complete_job(self, request, pk=None):
        """Technician marks job as completed"""
        job = self.get_object()
        if job.assigned_technician != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if job.status != 'in_progress':
            return Response({'error': 'Job must be in progress to complete'}, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = 'completed'
        job.save()
        
        return Response({
            'message': 'Job marked as completed. Waiting for customer approval to release payment.',
            'job': JobPostingSerializer(job).data
        })
    
    @action(detail=True, methods=['post'])
    def approve_completion(self, request, pk=None):
        """Customer approves job completion and releases payment"""
        job = self.get_object()
        if job.customer != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if job.status != 'completed':
            return Response({'error': 'Job must be completed first'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Release payment if exists
        from apps.payments.models import JobPayment, Wallet, PlatformEarnings
        from django.utils import timezone
        from django.db import transaction as db_transaction
        
        try:
            job_payment = job.job_payment
            if job_payment.status == 'held':
                with db_transaction.atomic():
                    # Credit technician's wallet
                    technician_wallet, _ = Wallet.objects.get_or_create(
                        user=job_payment.technician
                    )
                    technician_wallet.credit(
                        amount=job_payment.technician_amount,
                        transaction_type='earning',
                        reference=job_payment.payment_ref,
                        metadata={
                            'job_id': job.id,
                            'job_title': job.title,
                            'total_paid': str(job_payment.amount_paid),
                            'platform_fee': str(job_payment.platform_fee)
                        }
                    )
                    
                    # Update payment status
                    job_payment.status = 'released'
                    job_payment.released_at = timezone.now()
                    job_payment.save()
                    
                    # Update job payment status
                    job.payment_status = 'released'
                    job.save()
                
                return Response({
                    'message': f'Job approved! KES {job_payment.technician_amount} released to technician.',
                    'job': JobPostingSerializer(job).data,
                    'payment': {
                        'technician_amount': str(job_payment.technician_amount),
                        'platform_fee': str(job_payment.platform_fee)
                    }
                })
        except JobPayment.DoesNotExist:
            pass
        
        return Response({
            'message': 'Job approved!',
            'job': JobPostingSerializer(job).data
        })


class BidViewSet(viewsets.ModelViewSet):
    """ViewSet for bids - technicians place bids on jobs"""
    queryset = Bid.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BidCreateSerializer
        if self.action == 'list':
            return BidListSerializer
        return BidSerializer
    
    def get_queryset(self):
        """Technicians see their own bids"""
        return Bid.objects.filter(technician=self.request.user)
    
    def create(self, request):
        """Technician places a bid"""
        # Check if technician is verified
        try:
            profile = request.user.technician_profile
            if profile.kyc_status != 'approved':
                return Response(
                    {'error': 'You must complete KYC verification before bidding'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except:
            return Response(
                {'error': 'Technician profile not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BidCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            bid = serializer.save(technician=request.user)
            
            # Update job bid count
            job = bid.job
            job.total_bids = job.bids.count()
            job.save()
            
            return Response(BidSerializer(bid).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Technician withdraws their bid"""
        bid = self.get_object()
        if bid.technician != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if bid.status != 'pending':
            return Response({'error': 'Can only withdraw pending bids'}, status=status.HTTP_400_BAD_REQUEST)
        
        bid.status = 'withdrawn'
        bid.save()
        return Response({'message': 'Bid withdrawn'})
