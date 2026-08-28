from django.utils.text import slugify
from django.core.exceptions import ValidationError
from .models import Salon, SalonService, SalonImage, BusinessHours


def create_salon(manager, name, phone, address, city, country, opening_time, closing_time, slug=None, business_hours=None, **kwargs):
    if Salon.objects.filter(manager=manager).exists():
        raise ValidationError("This manager already manages a salon.")
    if not slug:
        slug = slugify(name)
        base_slug = slug
        counter = 1
        # salon can have the same across different locations
        while Salon.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

    salon = Salon.objects.create(
        manager=manager,
        name=name,
        slug=slug,
        phone=phone,
        address=address,
        city=city,
        country=country,
        opening_time=opening_time,
        closing_time=closing_time,
        **kwargs
    )

    if business_hours:
        for entry in business_hours:
            weekday = entry.get('weekday')
            if weekday is None:
                continue
            opening_time = entry.get('opening_time') or '00:00:00'
            closing_time = entry.get('closing_time') or '00:00:00'
            BusinessHours.objects.update_or_create(
                salon=salon,
                weekday=weekday,
                defaults={
                    'opening_time': opening_time,
                    'closing_time': closing_time,
                    'is_closed': entry.get('is_closed', False),
                }
            )
    else:
        # Auto-generate default business hours (Monday to Sunday)
        for day in range(7):
            BusinessHours.objects.get_or_create(
                salon=salon,
                weekday=day,
                defaults={
                    'opening_time': opening_time,
                    'closing_time': closing_time,
                    'is_closed': False
                }
            )

    return salon

def update_salon(salon, **kwargs):
    for field, value in kwargs.items():
        if hasattr(salon, field) and value is not None:
            setattr(salon, field, value)
    salon.save()
    return salon

def create_salon_service(salon, name=None, duration_minutes=None, price=None, description="", is_active=True, catalog_item=None, **kwargs):
    if catalog_item:
        if SalonService.objects.filter(salon=salon, catalog_item=catalog_item).exists():
            raise ValidationError(f"This salon already offers '{catalog_item.name}'.")
        if name is None:
            name = catalog_item.name
        if duration_minutes is None:
            duration_minutes = catalog_item.duration_minutes
        if price is None:
            price = catalog_item.price
        if not description:
            description = catalog_item.description
    return SalonService.objects.create(
        salon=salon,
        catalog_item=catalog_item,
        name=name,
        description=description,
        duration_minutes=duration_minutes,
        price=price,
        is_active=is_active
    )

# def update_salon_service(service, **kwargs):
#     for field, value in kwargs.items():
#         if hasattr(service, field) and value is not None:
#             setattr(service, field, value)
#     service.save()
#     return service


def update_salon_service(service, **kwargs):
    for field, value in kwargs.items():
        if value is None:
            continue
            
        if hasattr(service, field):
            # Check if this is a ForeignKey field
            field_obj = service._meta.get_field(field)
            if field_obj.is_relation and field_obj.many_to_one:
                # It's a ForeignKey - resolve the related instance if a raw id was passed
                related_model = field_obj.related_model
                if not isinstance(value, related_model):
                    value = related_model.objects.get(id=value)
            setattr(service, field, value)
    service.save()
    return service


def update_business_hours(business_hour, opening_time, closing_time, is_closed=False):
    business_hour.opening_time = opening_time
    business_hour.closing_time = closing_time
    business_hour.is_closed = is_closed
    business_hour.save()
    return business_hour
