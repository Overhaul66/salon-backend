from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalonViewSet, SalonServiceViewSet, ServiceCatalogViewSet

router = DefaultRouter()
router.register('salons', SalonViewSet, basename='salon')
router.register('services', SalonServiceViewSet, basename='service')
router.register('service-catalog', ServiceCatalogViewSet, basename='service-catalog')

urlpatterns = [
    path('', include(router.urls)),
]
