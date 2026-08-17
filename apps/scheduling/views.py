from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
import datetime
from django.utils.dateparse import parse_date

from .models import EmployeeAvailability
from .serializers import EmployeeAvailabilitySerializer
from .permissions import IsEmployeeOrManager
from .services import generate_employee_availability

class EmployeeAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAvailability.objects.all()
    serializer_class = EmployeeAvailabilitySerializer
    permission_classes = (permissions.IsAuthenticated, IsEmployeeOrManager)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('employee', 'date', 'status')
    tags = ['availabilities']


@extend_schema(
    tags=['my'],
    parameters=[
        OpenApiParameter('start_date', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD). Defaults to today.'),
        OpenApiParameter('end_date', OpenApiTypes.DATE, description='End date (YYYY-MM-DD). Defaults to start_date + 7 days.'),
    ],
    responses={200: EmployeeAvailabilitySerializer(many=True)},
)
class MyScheduleView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request):
        if request.user.role != 'SALON_EMPLOYEE' or not hasattr(request.user, 'employee_profile'):
            return Response(
                {"detail": "Only employees can access this endpoint."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        employee = request.user.employee_profile
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        try:
            start_date = parse_date(start_date_str) if start_date_str else datetime.date.today()
            end_date = parse_date(end_date_str) if end_date_str else start_date + datetime.timedelta(days=7)
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Ensure availability records exist for these dates (on-demand generation)
        curr_date = start_date
        while curr_date <= end_date:
            generate_employee_availability(employee, curr_date)
            curr_date += datetime.timedelta(days=1)
            
        availabilities = EmployeeAvailability.objects.filter(
            employee=employee,
            date__range=[start_date, end_date]
        ).order_by('date', 'start_time')
        
        serializer = EmployeeAvailabilitySerializer(availabilities, many=True)
        return Response(serializer.data)
