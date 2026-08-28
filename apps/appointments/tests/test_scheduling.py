import pytest
import datetime
from django.core.exceptions import ValidationError
from apps.users.models import CustomUser, Customer, SalonEmployee
from apps.salons.models import Salon, SalonService, BusinessHours
from apps.users.services import register_user
from apps.salons.services import create_salon, create_salon_service
from apps.scheduling.models import EmployeeAvailability
from apps.appointments.services import create_appointment, find_available_employee

@pytest.mark.django_db
class TestSchedulingEngine:
    @pytest.fixture(autouse=True)
    def setup(self):
        manager_user = register_user(
            email="manager@test.com",
            password="password123",
            role="SALON_MANAGER",
            phone="3333333333"
        )
        self.manager = manager_user.manager_profile
        
        self.salon = create_salon(
            manager=self.manager,
            name="Test Salon",
            phone="555-0000",

            address="123 Salon St",
            city="TestCity",
            country="TestCountry",
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0)
        )
        
        self.service = create_salon_service(
            salon=self.salon,
            name="Cut",
            duration_minutes=30,
            price=20.00
        )
        
        emp_u1 = register_user(
            email="emp1@test.com",
            password="password123",
            role="SALON_EMPLOYEE",
            salon=self.salon,
            position="Stylist",
            phone="1111111111",
            bio="Bio 1"
        )
        self.emp1 = emp_u1.employee_profile
        self.emp1.services.add(self.service)
        
        emp_u2 = register_user(
            email="emp2@test.com",
            password="password123",
            role="SALON_EMPLOYEE",
            salon=self.salon,
            position="Barber",
            phone="2222222222",
            bio="Bio 2"
        )
        self.emp2 = emp_u2.employee_profile
        self.emp2.services.add(self.service)
        
        cust_u = register_user(
            email="cust@test.com",
            password="password123",
            role="CUSTOMER",
            phone="4444444444"
        )
        self.customer = cust_u.customer_profile
        
        self.date = datetime.date.today() + datetime.timedelta(days=1)

    def test_scheduling_respects_business_hours(self):
        with pytest.raises(ValidationError) as exc:
            find_available_employee(self.salon, self.service, self.date, datetime.time(8, 30))
        assert "outside salon business hours" in str(exc.value)

    def test_create_salon_accepts_per_day_business_hours(self):
        # Use a different manager so we don't violate the one-salon-per-manager constraint
        other_manager_user = register_user(
            email="manager2@test.com",
            password="password123",
            role="SALON_MANAGER",
            phone="9999999999"
        )
        other_manager = other_manager_user.manager_profile

        salon = create_salon(
            manager=other_manager,
            name="Custom Hours Salon",
            phone="555-1111",

            address="456 Salon St",
            city="TestCity",
            country="TestCountry",
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0),
            business_hours=[
                {"weekday": 0, "opening_time": datetime.time(9, 30), "closing_time": datetime.time(17, 0), "is_closed": False},
                {"weekday": 1, "opening_time": datetime.time(10, 0), "closing_time": datetime.time(18, 0), "is_closed": False},
                {"weekday": 2, "opening_time": datetime.time(9, 0), "closing_time": datetime.time(17, 30), "is_closed": False},
                {"weekday": 6, "opening_time": datetime.time(11, 0), "closing_time": datetime.time(15, 0), "is_closed": False},
            ],
        )

        monday = salon.business_hours.get(weekday=0)
        assert monday.opening_time == datetime.time(9, 30)
        assert monday.closing_time == datetime.time(17, 0)
        sunday = salon.business_hours.get(weekday=6)
        assert sunday.opening_time == datetime.time(11, 0)
        assert sunday.closing_time == datetime.time(15, 0)

    def test_workload_balancing(self):
        # First booking - should go to one of them
        apt1 = create_appointment(
            customer=self.customer,
            salon=self.salon,
            service=self.service,
            date=self.date,
            start_time=datetime.time(10, 0)
        )
        assigned_emp = apt1.employee
        other_emp = self.emp2 if assigned_emp == self.emp1 else self.emp1
        
        # Second booking at same time - must balance workload and go to other employee
        apt2 = create_appointment(
            customer=self.customer,
            salon=self.salon,
            service=self.service,
            date=self.date,
            start_time=datetime.time(10, 0)
        )
        assert apt2.employee == other_emp

        # Third booking at same time - should fail as both are now booked
        with pytest.raises(ValidationError) as exc:
            create_appointment(
                customer=self.customer,
                salon=self.salon,
                service=self.service,
                date=self.date,
                start_time=datetime.time(10, 0)
            )
        assert "No employees are available" in str(exc.value)

    def test_employee_on_leave_excluded(self):
        EmployeeAvailability.objects.create(
            employee=self.emp1,
            date=self.date,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(18, 0),
            status='LEAVE'
        )
        
        emp = find_available_employee(self.salon, self.service, self.date, datetime.time(11, 0))
        assert emp == self.emp2
