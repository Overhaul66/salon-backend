import datetime
import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import CustomUser
from apps.salons.models import Salon, SalonImage, BusinessHours
from apps.appointments.models import Appointment
from apps.scheduling.models import EmployeeAvailability
from apps.notifications.models import Notification
from apps.users.services import register_user
from apps.salons.services import create_salon, create_salon_service
from apps.appointments.services import create_appointment
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


def open_file(name):
    """Return a Django File wrapping an image in the repo's salonData/ folder."""
    path = settings.BASE_DIR / 'salonData' / name
    if not os.path.exists(path):
        return None
    return File(open(path, 'rb'), name=name)

class Command(BaseCommand):
    help = ('Seeds real Ghanaian salons (using images in salonData/) with '
            'managers, employees, customers, services and gallery photos. '
            'Writes SEED_ACCOUNTS_GHANA.md listing every account.')

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
        accounts = []  # (role, email, label) tuples for the MD file

        # ============ 1. Superuser ============
        self.stdout.write("Creating superuser...")
        CustomUser.objects.create_superuser(
            email="admin@salon.com",
            password=password,
            first_name="System",
            last_name="Admin",
        )
        accounts.append(('Admin', 'admin@salon.com', 'Superuser / Admin'))

        # ============ 2. Managers & Salons ============
        self.stdout.write("Creating Ghanaian managers and salons...")
        salons = []
        salon_services = []
        services_for = {}
        employees = []
        customers = []

        salon_specs = [
            {
                "manager": ("amanfo@salon.com", "Adwoa", "Mensah", "+233-24-101-0001"),
                "salon": {
                    "name": "CBK Beauty Flagship Salon",
                    "phone": "+233-30-274-1001",
                    "address": "31 Kanda Highway, Ayawaso",
                    "city": "Accra",
                    "country": "Ghana",
                    "opening_time": datetime.time(8, 30),
                    "closing_time": datetime.time(19, 0),
                    "gender_type": "UNISEX",
                    "logo": "1787917813778_logo1.png",
                    "cover": "1787917813778_f9cd58a3-0114-45de-ad6c-eb6cb506877d-CBKBeautyFlagshipSalon-GH-GreaterAccraRegion-Accra-Ayawaso-Fresha.png",
                    "gallery": [
                        "1787917813778_f9cd58a3-0114-45de-ad6c-eb6cb506877d-CBKBeautyFlagshipSalon-GH-GreaterAccraRegion-Accra-Ayawaso-Fresha.png",
                    ],
                    "hours": week_hours(8, 19),
                },

                "employees": [
                    ("efua.stylist@salon.com", "Efua", "Boateng", "Senior Stylist", "Braids, weaves and precision cuts."),
                    ("akua.color@salon.com", "Akua", "Owusu", "Color Expert", "Balayage and vivid hair colouring."),
                ],
                "services": [
                    ("Signature Braids", 120, 250.00),
                    ("Weave Installation", 90, 180.00),
                    ("Hair Colouring", 90, 200.00),
                    ("Blowout & Silk Press", 45, 120.00),
                    ("Manicure", 30, 80.00),
                ],
            },
            {
                "manager": ("nana@salon.com", "Nana", "Asante", "+233-24-202-0002"),
                "salon": {
                    "name": "Indina Natural Hair Salon",
                    "phone": "+233-30-277-2002",
                    "address": "12 La Road, Kpeshie",
                    "city": "Accra",
                    "country": "Ghana",
                    "opening_time": datetime.time(9, 0),
                    "closing_time": datetime.time(18, 30),
                    "gender_type": "UNISEX",
                    "logo": "1787917813778_logo2.png",
                    "cover": "1787917813779_42156bee-fdf0-46ad-830e-e989ee92fbff-INDINATURALHAIRSALON-GH-GreaterAccraRegion-Accra-Kpeshie-Fresha.png",
                    "gallery": [
                        "1787917813779_42156bee-fdf0-46ad-830e-e989ee92fbff-INDINATURALHAIRSALON-GH-GreaterAccraRegion-Accra-Kpeshie-Fresha.png",
                        "1787917813779_a8cd79c0-2dbd-4efb-9c44-f2439b2b0a2b-INDINATURALHAIRSALON-GH-GreaterAccraRegion-Accra-Kpeshie-Fresha.png",
                    ],
                    "hours": week_hours(9, 18),
                },
                "employees": [
                    ("abena.locs@salon.com", "Abena", "Koranteng", "Natural Hair Specialist", "Loc maintenance, twists and scalp care."),
                    ("kojo.styler@salon.com", "Kojo", "Mensah", "Barber", "Classic cuts and beard sculpting."),
                ],
                "services": [
                    ("Loc Retwist & Style", 90, 160.00),
                    ("Twist Out / Braid Out", 60, 110.00),
                    ("Deep Conditioning", 45, 90.00),
                    ("Natural Hair Cut", 40, 70.00),
                    ("Scalp Treatment", 45, 85.00),
                ],
            },

            {
                "manager": ("yaa@salon.com", "Yaa", "Acheampong", "+233-24-303-0003"),
                "salon": {
                    "name": "The Gentlemen's Den Barbershop",
                    "phone": "+233-30-278-3003",
                    "address": "26 Oxford Street, Osu",
                    "city": "Accra",
                    "country": "Ghana",
                    "opening_time": datetime.time(9, 0),
                    "closing_time": datetime.time(21, 0),
                    "gender_type": "MEN_ONLY",
                    "logo": "1787917813777_man-hair-salon-logo-vector-illustration-white-background_1023984-42155.png",
                    "cover": "1787917813777_photo-1686671805337-7d8aa64b965f.png",
                    "gallery": [
                        "1787917813777_photo-1686671805337-7d8aa64b965f.png",
                    ],
                    "hours": week_hours(9, 21, closed_days=(6,)),
                },
                "employees": [
                    ("kwame.fade@salon.com", "Kwame", "Darko", "Master Barber", "Skin fades, tapers and hot-towel shaves."),
                    ("kofi.trim@salon.com", "Kofi", "Ampofo", "Barber", "Classic cuts and beard grooming."),
                ],
                "services": [
                    ("Skin Fade", 30, 60.00),
                    ("Classic Haircut", 30, 55.00),
                    ("Beard Trim & Shape", 20, 35.00),
                    ("Hot Towel Shave", 30, 50.00),
                    ("Hair + Beard Combo", 50, 95.00),
                ],
            },
            {
                "manager": ("ama@salon.com", "Ama", "Serwaa", "+233-24-404-0004"),
                "salon": {
                    "name": "Glam Beauty & Lash Studio",
                    "phone": "+233-30-279-4004",
                    "address": "8 Boundary Road, East Legon",
                    "city": "Accra",
                    "country": "Ghana",
                    "opening_time": datetime.time(9, 0),
                    "closing_time": datetime.time(19, 30),
                    "gender_type": "WOMEN_ONLY",
                    "logo": "1787917813777_logo3.png",
                    "cover": "1787917813777_photo-1686671805337-7d8aa64b965f.png",
                    "gallery": [
                        "1787917813779_42156bee-fdf0-46ad-830e-e989ee92fbff-INDINATURALHAIRSALON-GH-GreaterAccraRegion-Accra-Kpeshie-Fresha.png",
                    ],
                    "hours": week_hours(9, 19),
                },
                "employees": [
                    ("akosua.lash@salon.com", "Akosua", "Gyamfi", "Lash Technician", "Lash lifts, tints and extensions."),
                    ("efa.brows@salon.com", "Efa", "Addo", "Esthetician", "Brow shaping, facials and waxing."),
                ],
                "services": [
                    ("Classic Lash Extensions", 90, 220.00),
                    ("Lash Lift & Tint", 45, 130.00),
                    ("Eyebrow Shaping", 15, 40.00),
                    ("Deep Cleansing Facial", 50, 180.00),
                    ("Full Body Waxing", 60, 260.00),
                ],
            },
        ]


        # Build salons, attach images, create services & employees
        for spec in salon_specs:
            mgr_email, mgr_first, mgr_last, mgr_phone = spec["manager"]
            manager_user = register_user(
                email=mgr_email,
                password=password,
                role="SALON_MANAGER",
                first_name=mgr_first,
                last_name=mgr_last,
                phone=mgr_phone,
            )
            accounts.append(('Manager', mgr_email, spec["salon"]["name"]))

            s = spec["salon"]
            create_kwargs = {
                "gender_type": s["gender_type"],
                "business_hours": s["hours"],
            }
            salon = create_salon(
                manager=manager_user.manager_profile,
                name=s["name"],
                phone=s["phone"],
                address=s["address"],
                city=s["city"],
                country=s["country"],
                opening_time=s["opening_time"],
                closing_time=s["closing_time"],
                **create_kwargs,
            )

            # Attach logo + cover image (uploaded to S3 via default storage)
            salon.logo = open_file(s["logo"])
            salon.cover_image = open_file(s["cover"])
            salon.save()

            # Attach gallery images
            for order, img_name in enumerate(s.get("gallery", [])):
                f = open_file(img_name)
                if f:
                    SalonImage.objects.create(salon=salon, image=f, order=order)

            # Services
            salon_services_for_salon = []
            for svc_name, duration, price in spec["services"]:
                svc = create_salon_service(
                    salon, name=svc_name, duration_minutes=duration, price=price
                )
                salon_services_for_salon.append(svc)
            services_for[salon.id] = salon_services_for_salon
            salon_services.extend(salon_services_for_salon)

            # Employees
            for emp_email, emp_first, emp_last, position, bio in spec["employees"]:
                emp_user = register_user(
                    email=emp_email,
                    password=password,
                    role="SALON_EMPLOYEE",
                    first_name=emp_first,
                    last_name=emp_last,
                    phone="+233-24-5{:02d}-{:04d}".format(len(employees) + 1, len(employees) + 1),
                    salon=salon,
                    position=position,
                    bio=bio,
                )
                emp_user.employee_profile.services.set(salon_services_for_salon)
                employees.append(emp_user.employee_profile)
                accounts.append(('Employee', emp_email, f'{salon.name} — {position}'))

            salons.append(salon)
            self.stdout.write(f"  Salon: {salon.name}")

        # ============ 3. Customers ============
        self.stdout.write("Creating customers...")
        customer_specs = [
            ("kwesi.owusu@example.com", "Kwesi", "Owusu", "+233-24-600-0101", "MALE"),
            ("ama.danso@example.com", "Ama", "Danso", "+233-24-600-0102", "FEMALE"),
            ("kofi.antwi@example.com", "Kofi", "Antwi", "+233-24-600-0103", "MALE"),
            ("efua.mensah@example.com", "Efua", "Mensah", "+233-24-600-0104", "FEMALE"),
        ]
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
            accounts.append(('Customer', email, f'{first} {last}'))


        # ============ 4. Availabilities ============
        self.stdout.write("Generating employee availabilities for the next 7 days...")
        for employee in employees:
            for offset in range(7):
                generate_employee_availability(employee, today + datetime.timedelta(days=offset))

        # ============ 5. A few sample appointments ============
        self.stdout.write("Booking sample appointments...")
        for i, salon in enumerate(salons):
            own = services_for[salon.id]
            if not own:
                continue
            customer = customers[i % len(customers)]
            service = own[i % len(own)]
            date = today + datetime.timedelta(days=1)
            if BusinessHours.objects.filter(salon=salon, weekday=date.weekday(), is_closed=True).exists():
                continue
            try:
                create_appointment(
                    customer=customer,
                    salon=salon,
                    service=service,
                    date=date,
                    start_time=datetime.time(11, 0),
                    booking_notes="Sample booking from Ghana seed data.",
                )
            except Exception as e:
                self.stderr.write(f"  Skipped appointment for {salon.name}: {e}")

        # ============ 6. Write the accounts MD file ============
        md_path = settings.BASE_DIR / "SEED_ACCOUNTS_GHANA.md"
        self.write_accounts_md(md_path, accounts, password)

        self.stdout.write(self.style.SUCCESS("Ghana database seeded successfully!"))
        self.stdout.write("")
        self.stdout.write(f"Accounts written to {md_path}")
        self.stdout.write(f"Stats: {len(salons)} salons, {len(salon_services)} services, "
                         f"{len(employees)} employees, {len(customers)} customers.")

    def write_accounts_md(self, path, accounts, password):
        rows = {'Admin': [], 'Manager': [], 'Employee': [], 'Customer': []}
        for role, email, label in accounts:
            rows[role].append((email, label))

        def table(rows_list, label_heading):
            lines = [f"| Email | {label_heading} |", "| --- | --- |"]
            for email, label in rows_list:
                lines.append(f"| {email} | {label} |")
            return "\n".join(lines)

        content = []
        content.append("# Seed Accounts — Ghana\n")
        content.append("Populated by `docker compose exec web python manage.py seed_ghana`.\n")
        content.append(f"All accounts use the password: **`{password}`**\n")
        content.append("## Admin\n")
        content.append(table(rows['Admin'], "Role") + "\n")
        content.append("## Salon Managers\n")
        content.append(table(rows['Manager'], "Salon") + "\n")
        content.append("## Employees\n")
        content.append(table(rows['Employee'], "Salon — Position") + "\n")
        content.append("## Customers\n")
        content.append(table(rows['Customer'], "Name") + "\n")

        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(content))

