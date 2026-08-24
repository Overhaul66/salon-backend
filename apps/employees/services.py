from django.core.exceptions import ValidationError
from django.db import transaction
from apps.users.models import CustomUser, SalonEmployee
from apps.users.services import register_user

def check_manager_owns_salon(manager, salon):
    if salon.manager != manager:
        raise ValidationError("You do not own this salon.")

@transaction.atomic
def create_salon_employee(manager, email, password, salon, first_name="", last_name="", phone="", bio="", profile_picture=None, services=None):
    check_manager_owns_salon(manager, salon)
    
    services = services or []
    for service in services:
        if service.salon_id != salon.id:
            raise ValidationError("All selected services must belong to the employee's salon.")

    user = register_user(
        email=email,
        password=password,
        role='SALON_EMPLOYEE',
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        profile_picture=profile_picture,
        # Profile fields
        salon=salon,
        position="",
        bio=bio,
        is_available=True
    )
    
    employee = user.employee_profile
    if services:
        employee.services.set(services)
    
    return employee

@transaction.atomic
def update_salon_employee(manager, employee, **kwargs):
    if employee.salon.manager != manager:
        raise ValidationError("This employee does not work at your salon.")
        
    user = employee.user
    
    # Update CustomUser fields
    user_fields = ['first_name', 'last_name', 'phone', 'is_active']
    for field in user_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(user, field, kwargs[field])
    user.save()
    
    # Update SalonEmployee fields
    profile_fields = ['position', 'bio', 'is_available', 'employment_date']
    for field in profile_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(employee, field, kwargs[field])
    employee.save()

    # Update M2M services
    services = kwargs.pop('services', None)
    if services is not None:
        for service in services:
            if service.salon_id != employee.salon_id:
                raise ValidationError("All selected services must belong to the employee's salon.")
        employee.services.set(services)
    
    return employee

@transaction.atomic
def reset_employee_password(manager, employee, new_password):
    if employee.salon.manager != manager:
        raise ValidationError("This employee does not work at your salon.")
    user = employee.user
    user.set_password(new_password)
    user.save()
