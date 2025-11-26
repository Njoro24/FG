from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import TechnicianAvailability, TechnicianLocation
from .serializers import TechnicianAvailabilitySerializer, TechnicianLocationSerializer
from apps.accounts.permissions import IsTechnician


class TechnicianAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = TechnicianAvailability.objects.all()
    serializer_class = TechnicianAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsTechnician]
    
    def get_queryset(self):
        return TechnicianAvailability.objects.filter(technician=self.request.user)


class TechnicianLocationViewSet(viewsets.ModelViewSet):
    queryset = TechnicianLocation.objects.all()
    serializer_class = TechnicianLocationSerializer
    permission_classes = [IsAuthenticated, IsTechnician]
    
    def get_queryset(self):
        return TechnicianLocation.objects.filter(technician=self.request.user)
