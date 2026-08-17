import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import CustomUser
from apps.salons.models import Salon, BusinessHours
from apps.appointments.models import Appointment
from apps.scheduling.models import EmployeeAvailability
from apps.notifications.models import Notification
from apps.users.services import register_user
from apps.salons.services import create_salon, create_salon_service
from apps.appointments.services import create_appointment, cancel_appointment, update_appointment_status
from apps.scheduling.services import generate_employee_availability


def week_hours(open_hour, close_hour, closed_days=()):
    """Build a full 7-day business-hours payload for create_salon."""
    hours = []
    for day in range(7):
        closed = day in closed_days
        hours.append({
            'weekday': day,
            'opening_time': '00:00' if closed else f'{open_hour:02d}:00',
            'closing_time': '00:00' if closed else f'{close_hour:02d}:00',
            'is_closed': closed,
        })
    return hours


class Command(BaseCommand):
    help = 'Seeds the database with managers, salons, services, employees, customers, appointments, availabilities and notifications.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Clearing existing data...")
        Appointment.objects.all().delete()
        EmployeeAvailability.objects.all().delete()
        Notification.objects.all().delete()
        Salon.objects.all().delete()
        CustomUser.objects.all().delete()

        today = datetime.date.today()
        password = "password123"

        # ============ 1. Superuser ============
        self.stdout.write("Creating superuser...")
        CustomUser.objects.create_superuser(
            email="admin@salon.com",
            password=password,
            first_name="System",
            last_name="Admin",
        )

        # ============ 2. Managers & Salons ============
        self.stdout.write("Creating managers and salons...")
        manager_data = [
            {
                "email": "alice@salon.com",
                "first_name": "Alice",
                "last_name": "Smith",
                "phone": "+1-555-0101",
                "salon": {
                    "name": "Glow & Co Beauty Studio",
                    "phone": "+1-555-1001",
                    "address": "123 Beauty Lane, Downtown",
                    "city": "Seattle",
                    "country": "USA",
                    "opening_time": datetime.time(9, 0),
                    "closing_time": datetime.time(18, 0),
                    "gender_type": "UNISEX",
                    "hours": week_hours(9, 18),
                },
            },
            {
                "email": "bob@salon.com",
                "first_name": "Bob",
                "last_name": "Johnson",
                "phone": "+1-555-0102",
                "salon": {
                    "name": "The Gentleman's Lounge",
                    "phone": "+1-555-1002",
                    "address": "456 Grooming Blvd",
                    "city": "Seattle",
                    "country": "USA",
                    "opening_time": datetime.time(10, 0),
                    "closing_time": datetime.time(20, 0),
                    "gender_type": "MEN_ONLY",
                    "hours": week_hours(10, 20, closed_days=(6,)),
                },
            },
            {
                "email": "carol@salon.com",
                "first_name": "Carol",
                "last_name": "Williams",
                "phone": "+1-555-0103",
                "salon": {
                    "name": "Tranquil Spa & Studio",
                    "phone": "+1-555-1003",
                    "address": "789 Wellness Way",
                    "city": "Portland",
                    "country": "USA",
                    "opening_time": datetime.time(8, 0),
                    "closing_time": datetime.time(17, 0),
                    "gender_type": "WOMEN_ONLY",
                    "hours": week_hours(8, 17),
                },
            },
        ]

        salons = []
        for m in manager_data:
            manager_user = register_user(
                email=m["email"],
                password=password,
                role="SALON_MANAGER",
                first_name=m["first_name"],
                last_name=m["last_name"],
                phone=m["phone"],
            )
            s = m["salon"]
            salon = create_salon(
                manager=manager_user.manager_profile,
                name=s["name"],
                phone=s["phone"],
                address=s["address"],
                city=s["city"],
                country=s["country"],
                opening_time=s["opening_time"],
                closing_time=s["closing_time"],
                gender_type=s["gender_type"],
                business_hours=s["hours"],
            )
            salons.append(salon)
            self.stdout.write(f"  Salon: {salon.name}")

        # ============ 3. Services ============
        self.stdout.write("Creating salon services...")
        services_by_salon = [
            [
                ("Signature Haircut", 45, 45.00),
                ("Hair Coloring", 90, 85.00),
                ("Deep Conditioning", 30, 35.00),
                ("Blowout & Style", 30, 40.00),
                ("Manicure", 30, 25.00),
                ("Pedicure", 45, 35.00),
            ],
            [
                ("Classic Haircut", 30, 30.00),
                ("Beard Trim & Shape", 20, 18.00),
                ("Hot Towel Shave", 30, 28.00),
                ("Hair + Beard Combo", 50, 45.00),
                ("Scalp Massage", 20, 20.00),
            ],
            [
                ("Full Body Massage", 60, 70.00),
                ("Facial Treatment", 45, 55.00),
                ("Spa Manicure", 45, 40.00),
                ("Hair Spa Ritual", 60, 65.00),
                ("Eyebrow Shaping", 15, 12.00),
                ("Waxing Session", 30, 35.00),
            ],
        ]
        salon_services = []
        for salon, svc_list in zip(salons, services_by_salon):
            for name, duration, price in svc_list:
                salon_services.append(create_salon_service(salon, name, duration, price))
        self.stdout.write(f"  {len(salon_services)} services created")

        # ============ 4. Employees ============
        self.stdout.write("Creating employees...")
        employee_specs = {
            0: [
                ("john.stylist@salon.com", "John", "Carter", "Senior Stylist", "Haircut specialist with 10 years of experience."),
                ("mary.color@salon.com", "Mary", "Bennett", "Color Expert", "Master colorist trained in Paris."),
                ("lisa.nails@salon.com", "Lisa", "Nguyen", "Nail Technician", "Manicures and pedicures with artistic flair."),
                ("peter.blow@salon.com", "Peter", "Davis", "Junior Stylist", "Fresh talent, eager to give you a great look."),
            ],
            1: [
                ("tom.barber@salon.com", "Tom", "Miller", "Master Barber", "Classic cuts and straight-razor shaves."),
                ("sam.fades@salon.com", "Sam", "Okafor", "Barber", "Modern fades and beard sculpting."),
                ("jay.crew@salon.com", "Jay", "Peters", "Barber", "Precision clipper work and hot towel shaves."),
            ],
            2: [
                ("anna.massage@salon.com", "Anna", "Lopez", "Massage Therapist", "Certified therapist specialising in deep tissue."),
                ("emma.facial@salon.com", "Emma", "Green", "Esthetician", "Facials and skin care treatments."),
                ("nina.wax@salon.com", "Nina", "Kaur", "Beauty Therapist", "Waxing, brows and spa rituals."),
            ],
        }
        employees = []
        for idx, salon in enumerate(salons):
            for email, first, last, position, bio in employee_specs[idx]:
                emp_user = register_user(
                    email=email,
                    password=password,
                    role="SALON_EMPLOYEE",
                    first_name=first,
                    last_name=last,
                    phone="+1-555-02{:02d}".format(idx * 10 + len(employees) + 1),
                    salon=salon,
                    position=position,
                    bio=bio,
                )
                employees.append(emp_user.employee_profile)
        self.stdout.write(f"  {len(employees)} employees created")

        # ============ 5. Customers ============
        self.stdout.write("Creating customers...")
        customer_specs = [
            ("charles.brown@example.com", "Charles", "Brown", "+1-555-0301", "MALE"),
            ("dana.scully@example.com", "Dana", "Scully", "+1-555-0302", "FEMALE"),
            ("emily.davis@example.com", "Emily", "Davis", "+1-555-0303", "FEMALE"),
            ("michael.wilson@example.com", "Michael", "Wilson", "+1-555-0304", "MALE"),
            ("sarah.taylor@example.com", "Sarah", "Taylor", "+1-555-0305", "FEMALE"),
            ("james.anderson@example.com", "James", "Anderson", "+1-555-0306", "MALE"),
            ("olivia.martin@example.com", "Olivia", "Martin", "+1-555-0307", "FEMALE"),
            ("liam.thomas@example.com", "Liam", "Thomas", "+1-555-0308", "MALE"),
        ]
        customers = []
        for email, first, last, phone, gender in customer_specs:
            user = register_user(
                email=email,
                password=password,
                role="CUSTOMER",
                first_name=first,
                last_name=last,
                phone=phone,
                gender=gender,
                preferred_notification="EMAIL",
            )
            customers.append(user.customer_profile)
        self.stdout.write(f"  {len(customers)} customers created")

        # ============ 6. Availabilities ============
        self.stdout.write("Generating employee availabilities for the next 14 days...")
        for employee in employees:
            for offset in range(14):
                generate_employee_availability(employee, today + datetime.timedelta(days=offset))

        # ============ 7. Appointments ============
        self.stdout.write("Booking appointments...")
        # (day_offset, start_hour, start_minute) slots used across salons
        upcoming_slots = [
            (1, 10, 0), (1, 11, 30), (1, 14, 0), (1, 16, 0),
            (2, 10, 0), (2, 13, 30), (2, 15, 30),
            (3, 11, 0), (3, 14, 30),
        ]
        past_slots = [
            (-3, 10, 0), (-3, 14, 0),
            (-2, 11, 0), (-2, 15, 0),
            (-1, 10, 30), (-1, 13, 0),
        ]

        # Completed appointments in the past
        for (day, h, m) in past_slots:
            for i, salon in enumerate(salons):
                if day == -3 and i == 2:
                    continue
                date = today + datetime.timedelta(days=day)
                if BusinessHours.objects.filter(salon=salon, weekday=date.weekday(), is_closed=True).exists():
                    continue
                customer = customers[(len(salons) + i) % len(customers)]
                service = salon_services[i * 6 % len(salon_services)]
                try:
                    appointment = create_appointment(
                        customer=customer,
                        salon=salon,
                        service=service,
                        date=date,
                        start_time=datetime.time(h, m),
                        booking_notes="Routine visit.",
                    )
                    update_appointment_status(appointment, 'COMPLETED')
                except Exception as e:
                    self.stderr.write(f"  Skipped past appointment ({salon.name} {date} {h}:{m}): {e}")

        # No-show appointment yesterday
        try:
            no_show = create_appointment(
                customer=customers[3],
                salon=salons[0],
                service=salon_services[0],
                date=today - datetime.timedelta(days=1),
                start_time=datetime.time(9, 0),
                booking_notes="Did not show up.",
            )
            update_appointment_status(no_show, 'NO_SHOW')
        except Exception as e:
            self.stderr.write(f"  Skipped no-show appointment: {e}")

        # Upcoming appointments with mixed statuses
        statuses = ['CONFIRMED', 'PENDING', 'CONFIRMED', 'CONFIRMED', 'PENDING', 'CONFIRMED', 'CANCELLED', 'CONFIRMED', 'CONFIRMED']
        for idx, (day, h, m) in enumerate(upcoming_slots):
            salon = salons[idx % len(salons)]
            date = today + datetime.timedelta(days=day)
            if BusinessHours.objects.filter(salon=salon, weekday=date.weekday(), is_closed=True).exists():
                continue
            customer = customers[idx % len(customers)]
            service = salon_services[idx % len(salon_services)]
            status = statuses[idx % len(statuses)]
            try:
                appointment = create_appointment(
                    customer=customer,
                    salon=salon,
                    service=service,
                    date=date,
                    start_time=datetime.time(h, m),
                    booking_notes=f"Appointment request for {service.name}.",
                )
                if status == 'CANCELLED':
                    cancel_appointment(appointment, "Customer had a schedule conflict.")
                elif status == 'PENDING':
                    appointment.status = 'PENDING'
                    appointment.save()
            except Exception as e:
                self.stderr.write(f"  Skipped upcoming appointment ({salon.name} {date} {h}:{m}): {e}")

        # Today's appointments (mix of in progress / confirmed)
        for h in (9, 11, 14):
            salon = salons[h % len(salons)]
            if BusinessHours.objects.filter(salon=salon, weekday=today.weekday(), is_closed=True).exists():
                continue
            customer = customers[(h + 4) % len(customers)]
            service = salon_services[(h + 2) % len(salon_services)]
            try:
                appointment = create_appointment(
                    customer=customer,
                    salon=salon,
                    service=service,
                    date=today,
                    start_time=datetime.time(h, 0),
                    booking_notes="Today's booking.",
                )
                if h == 9:
                    update_appointment_status(appointment, 'IN_PROGRESS')
                elif h == 11:
                    appointment.status = 'CONFIRMED'
                    appointment.save()
            except Exception as e:
                self.stderr.write(f"  Skipped today appointment ({salon.name} {h}:00): {e}")

        # ============ 8. Extra notifications ============
        self.stdout.write("Creating sample notifications...")
        from apps.notifications.services import send_notification
        send_notification(
            user=customers[0].user,
            title="Welcome to Glow & Co",
            message="Your account is ready. Book your first appointment today!",
        )
        Notification.objects.filter(user=customers[0].user).update(is_read=True)
        send_notification(
            user=employees[0].user,
            title="Shift Reminder",
            message="Don't forget your shift tomorrow at 9:00 AM.",
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
        self.stdout.write("")
        self.stdout.write("Accounts (password: password123):")
        self.stdout.write("  Admin:    admin@salon.com")
        self.stdout.write("  Manager:  alice@salon.com / bob@salon.com / carol@salon.com")
        self.stdout.write("  Employee: john.stylist@salon.com / tom.barber@salon.com / anna.massage@salon.com")
        self.stdout.write("  Customer: charles.brown@example.com / dana.scully@example.com")
        self.stdout.write("")
        self.stdout.write(f"Stats: {len(salons)} salons, {len(salon_services)} services, {len(employees)} employees, {len(customers)} customers, {Appointment.objects.count()} appointments, {EmployeeAvailability.objects.count()} availabilities, {Notification.objects.count()} notifications.")
