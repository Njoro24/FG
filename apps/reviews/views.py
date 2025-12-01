from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Use is_technician field instead of non-existent user_type
        if user.is_technician:
            return Review.objects.filter(technician=user)
        else:
            return Review.objects.filter(customer=user)
    
    def create(self, request):
        # Only customers can create reviews
        if request.user.is_technician:
            return Response(
                {'error': 'Technicians cannot create reviews'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReviewCreateSerializer(data=request.data)
        if serializer.is_valid():
            review = serializer.save(customer=request.user)
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
