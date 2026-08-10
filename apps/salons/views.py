from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.exceptions import PermissionDenied

from apps.users.permissions import IsSalonManager
from .models import Salon, SalonService, SalonImage, BusinessHours
from .serializers import SalonSerializer, SalonServiceSerializer, SalonImageSerializer, BusinessHoursSerializer
from .services import create_salon, update_salon, create_salon_service, update_salon_service
from .selectors import list_salons
from .permissions import IsSalonOwnerOrReadOnly

class SalonViewSet(viewsets.ModelViewSet):
    queryset = Salon.objects.all()
    serializer_class = SalonSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_fields = ('city', 'gender_type', 'status')
    search_fields = ('name', 'description', 'city')
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [permissions.IsAuthenticated(), IsSalonManager()]
        elif self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsSalonOwnerOrReadOnly()]
        return [permissions.AllowAny()]
        
    def get_queryset(self):
        # For listing and details: customers filter active salons.
        if self.action in ['list']:
            return list_salons(
                city=self.request.query_params.get('city'),
                service_name=self.request.query_params.get('service'),
                gender_type=self.request.query_params.get('gender'),
                min_rating=self.request.query_params.get('rating'),
                ordering=self.request.query_params.get('ordering'),
                lat=self.request.query_params.get('lat'),
                lon=self.request.query_params.get('lon')
            )
        return super().get_queryset()
        
    def perform_create(self, serializer):
        manager_profile = self.request.user.manager_profile
        salon = create_salon(
            manager=manager_profile,
            **serializer.validated_data
        )
        serializer.instance = salon
    
    # salon manager can get a list of all salon he own, update and delete
    @action(detail=False, methods=['get', 'patch', 'delete'], permission_classes=[permissions.IsAuthenticated, IsSalonManager])
    def me(self, request):
        manager_profile = request.user.manager_profile
        salons = Salon.objects.filter(manager=manager_profile)
        
        if request.method == 'GET':
            serializer = self.get_serializer(salons, many=True)
            return Response(serializer.data)
            
        elif request.method == 'PATCH':
            salon_id = request.data.get('id')
            if not salon_id:
                return Response({"detail": "Field 'id' (salon ID) is required to update."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                salon = salons.get(id=salon_id)
            except Salon.DoesNotExist:
                return Response({"detail": "Salon not found or does not belong to you."}, status=status.HTTP_404_NOT_FOUND)
                
            serializer = self.get_serializer(salon, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            updated = update_salon(salon, **serializer.validated_data)
            return Response(self.get_serializer(updated).data)
            
        elif request.method == 'DELETE':
            salon_id = request.data.get('id')
            if not salon_id:
                return Response({"detail": "Field 'id' (salon ID) is required to delete."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                salon = salons.get(id=salon_id)
            except Salon.DoesNotExist:
                return Response({"detail": "Salon not found or does not belong to you."}, status=status.HTTP_404_NOT_FOUND)
            salon.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class SalonServiceViewSet(viewsets.ModelViewSet):
    queryset = SalonService.objects.all()
    serializer_class = SalonServiceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('salon', 'is_active')
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSalonOwnerOrReadOnly()]
        return [permissions.AllowAny()]
        
    def perform_create(self, serializer):
        salon_id = serializer.validated_data.get('salon')
        try:
            salon = Salon.objects.get(id=salon_id, manager__user=self.request.user)
        except Salon.DoesNotExist:
            raise PermissionDenied("You do not own this salon.")
        
        validated_data = {**serializer.validated_data, 'salon': salon}
        service = create_salon_service(**validated_data)
        serializer.instance = service
        
    def perform_update(self, serializer):
        updated = update_salon_service(self.get_object(), **serializer.validated_data)
        serializer.instance = updated
