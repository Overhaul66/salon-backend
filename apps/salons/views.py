from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema

from apps.users.permissions import IsSalonManager
from .models import Salon, SalonService, SalonImage, BusinessHours, ServiceCatalog, SalonFavourite
from .serializers import SalonSerializer, SalonServiceSerializer, SalonImageSerializer, BusinessHoursSerializer, SalonCreateSerializer, ServiceCatalogSerializer
from .services import create_salon, update_salon, create_salon_service, update_salon_service
from .selectors import list_salons
from .permissions import IsSalonOwnerOrReadOnly

class ServiceCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCatalog.objects.filter(is_active=True)
    serializer_class = ServiceCatalogSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('category',)
    pagination_class = None
    permission_classes = (permissions.AllowAny,)
    tags = ['service-catalog']

class SalonViewSet(viewsets.ModelViewSet):
    queryset = Salon.objects.all()
    serializer_class = SalonSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_fields = ('city', 'gender_type', 'status')
    search_fields = ('name', 'description', 'city')
    tags = ['salons']

    def get_serializer_class(self):
        if self.action == 'create':
            return SalonCreateSerializer
        if self.action in ['update', 'partial_update']:
            return SalonCreateSerializer
        return SalonSerializer
    
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
        business_hours = serializer.validated_data.pop('business_hours', [])
        salon = create_salon(
            manager=manager_profile,
            business_hours=business_hours,
            **serializer.validated_data
        )
        serializer.instance = salon
    
    # salon manager can get a list of all salon he own, update and delete
    @extend_schema(
        methods=['GET'],
        request=None,
        responses={200: {'type': 'array', 'items': {'$ref': '#/components/schemas/Salon'}}},
    )
    @extend_schema(
        methods=['PATCH'],
        request=SalonCreateSerializer,
        responses={200: SalonSerializer},
    )
    @extend_schema(
        methods=['DELETE'],
        request=None,
        responses={204: None},
    )
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

    def get_customer(self, request):
        if request.user.role != 'CUSTOMER' or not hasattr(request.user, 'customer_profile'):
            raise PermissionDenied("Only customers can manage salon favourites.")
        return request.user.customer_profile

    @extend_schema(
        request=None,
        responses={200: SalonSerializer},
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def favourite(self, request, pk=None):
        customer = self.get_customer(request)
        salon = self.get_object()
        SalonFavourite.objects.get_or_create(customer=customer, salon=salon)
        return Response(self.get_serializer(salon).data)

    @extend_schema(
        request=None,
        responses={200: SalonSerializer},
    )
    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def unfavourite(self, request, pk=None):
        customer = self.get_customer(request)
        salon = self.get_object()
        SalonFavourite.objects.filter(customer=customer, salon=salon).delete()
        return Response(self.get_serializer(salon).data)

    @extend_schema(
        request=None,
        responses={200: SalonSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def favourites(self, request):
        customer = self.get_customer(request)
        salons = Salon.objects.filter(
            favourited_by__customer=customer,
            status='ACTIVE'
        ).order_by('-favourited_by__created_at')
        page = self.paginate_queryset(salons)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(salons, many=True)
        return Response(serializer.data)


class SalonServiceViewSet(viewsets.ModelViewSet):
    queryset = SalonService.objects.all()
    serializer_class = SalonServiceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('salon', 'is_active')
    tags = ['services']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        salons_param = self.request.query_params.get('salons')
        if salons_param:
            salon_ids = [s for s in salons_param.split(',') if s]
            if salon_ids:
                queryset = queryset.filter(salon_id__in=salon_ids)
        return queryset
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSalonOwnerOrReadOnly()]
        return [permissions.AllowAny()]
        
    def perform_create(self, serializer):
        salon = serializer.validated_data.get('salon')
        try:
            owned = Salon.objects.get(id=salon.id, manager__user=self.request.user)
        except Salon.DoesNotExist:
            raise PermissionDenied("You do not own this salon.")
        
        validated_data = {**serializer.validated_data, 'salon': owned}
        service = create_salon_service(**validated_data)
        serializer.instance = service
        
    def perform_update(self, serializer):
        salon = serializer.validated_data.get('salon')
        if salon is not None:
            try:
                owned = Salon.objects.get(id=salon.id, manager__user=self.request.user)
            except Salon.DoesNotExist:
                raise PermissionDenied("You do not own this salon.")
            serializer.validated_data['salon'] = owned
        updated = update_salon_service(self.get_object(), **serializer.validated_data)
        serializer.instance = updated
