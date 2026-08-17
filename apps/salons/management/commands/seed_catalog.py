from django.core.management.base import BaseCommand
from apps.salons.models import ServiceCatalog

CATALOG = [
    # MEN
    ("Classic Haircut", "Classic haircut tailored to your style.", 30, "30.00", "MEN"),
    ("Beard Trim & Shape", "Neat trim and shape-up for your beard.", 20, "18.00", "MEN"),
    ("Hair + Beard Combo", "Haircut and beard trim in one session.", 50, "45.00", "MEN"),
    ("Hot Towel Shave", "Traditional hot towel straight-razor shave.", 30, "28.00", "MEN"),
    ("Scalp Massage", "Relaxing head and scalp massage.", 20, "20.00", "MEN"),
    ("Hair Colouring", "Full colour application for men.", 90, "120.00", "MEN"),
    ("Kids Haircut", "Friendly haircut for children.", 20, "20.00", "MEN"),
    # WOMEN
    ("Haircut & Style", "Cut and style your hair to perfection.", 60, "80.00", "WOMEN"),
    ("Wash & Blow Dry", "Shampoo, condition and blow-dry finish.", 45, "60.00", "WOMEN"),
    ("Hair Treatment", "Deep conditioning hair treatment.", 45, "90.00", "WOMEN"),
    ("Hair Colouring / Highlights", "Full colour or highlights.", 120, "180.00", "WOMEN"),
    ("Braids / Weaves", "Braiding or weave installation.", 150, "150.00", "WOMEN"),
    ("Facial Treatment", "Deep-cleansing facial treatment.", 45, "55.00", "WOMEN"),
    ("Spa Manicure", "Nails cleaned, shaped and pampered.", 45, "40.00", "WOMEN"),
    ("Spa Pedicure", "Feet exfoliated and nails perfected.", 45, "45.00", "WOMEN"),
    ("Waxing Session", "Smooth waxing for any area.", 30, "35.00", "WOMEN"),
    ("Eyebrow Shaping", "Precision eyebrow shaping.", 15, "12.00", "WOMEN"),
    ("Full Body Massage", "Full-body relaxation massage.", 60, "70.00", "WOMEN"),
    ("Hair Spa Ritual", "Complete hair spa ritual.", 60, "65.00", "WOMEN"),
    # UNISEX
    ("Deep Tissue Massage", "Deep muscle release massage.", 60, "90.00", "UNISEX"),
    ("Bridal Makeup", "Complete bridal makeup application.", 90, "200.00", "UNISEX"),
    ("Gel Nails", "Long-lasting gel nail application.", 45, "60.00", "UNISEX"),
    ("Threading", "Facial hair threading.", 15, "10.00", "UNISEX"),
]


class Command(BaseCommand):
    help = "Seeds the service catalog with the standard salon services."

    def handle(self, *args, **options):
        created = 0
        for name, description, duration, price, category in CATALOG:
            _, was_created = ServiceCatalog.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "duration_minutes": duration,
                    "price": price,
                    "category": category,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Catalog seeded. {created} new, {len(CATALOG) - created} already present."))