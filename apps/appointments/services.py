import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from apps.salons.models import Salon, SalonService, BusinessHours
from apps.users.models import SalonEmployee
from apps.scheduling.models import EmployeeAvailability
from apps.scheduling.services import generate_employee_availability
from .models import Appointment

def calculate_end_time(start_time, duration_minutes):
    dummy_date = datetime.date(2000, 1, 1)
    start_dt = datetime.datetime.combine(dummy_date, start_time)
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
    return end_dt.time()

def find_available_employee(salon, service, date, start_time):
    """
    Finds the best available employee for a service on a given date and time.
    Only employees who can perform the service are considered.
    Workload balance is achieved by selecting the employee with the minimum number
    of appointments already assigned for that day.
    """
    duration = service.duration_minutes
    end_time = calculate_end_time(start_time, duration)
    
    # 1. Respect Salon Business Hours
    weekday = date.weekday()
    try:
        hours = BusinessHours.objects.get(salon=salon, weekday=weekday)
        if hours.is_closed:
            raise ValidationError("The salon is closed on this day.")
        if start_time < hours.opening_time or end_time > hours.closing_time:
            raise ValidationError(f"The requested time is outside salon business hours ({hours.opening_time} - {hours.closing_time}).")
    except BusinessHours.DoesNotExist:
        if start_time < salon.opening_time or end_time > salon.closing_time:
            raise ValidationError(f"The requested time is outside salon business hours ({salon.opening_time} - {salon.closing_time}).")

    # Active employees of this salon who can perform this service
    eligible = SalonEmployee.objects.filter(salon=salon, is_available=True, services=service)
    if not eligible.exists():
        raise ValidationError("No employee at this salon currently performs this service.")
    
    # Only a single employee can do this service — surface a clear "busy" message
    single_employee = eligible.count() == 1

    candidates = []
    
    for employee in eligible:
        # On-demand generate availability
        generate_employee_availability(employee, date)
        
        # Check blocked schedules (LEAVE, BREAK, BOOKED)
        blocked = EmployeeAvailability.objects.filter(
            employee=employee,
            date=date,
            status__in=['BREAK', 'LEAVE', 'BOOKED']
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        ).exists()
        
        if blocked:
            continue
            
        # Check overlapping appointments
        overlapping_appointments = Appointment.objects.filter(
            employee=employee,
            appointment_date=date,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        ).exists()
        
        if overlapping_appointments:
            continue
            
        # Calculate workload (number of appointments assigned on this date)
        workload = Appointment.objects.filter(
            employee=employee,
            appointment_date=date,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
        ).count()
        
        candidates.append((employee, workload))
        
    if not candidates:
        if single_employee:
            raise ValidationError("The stylist who performs this service is busy at that time. Please choose another date or time.")
        raise ValidationError("No employees are available at this date and time.")
        
    # Balance workload (select candidate with lowest workload)
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]

@transaction.atomic
def create_appointment(customer, salon, service, date, start_time, booking_notes=""):
    employee = find_available_employee(salon, service, date, start_time)
    duration = service.duration_minutes
    end_time = calculate_end_time(start_time, duration)
    
    appointment = Appointment.objects.create(
        customer=customer,
        salon=salon,
        employee=employee,
        service=service,
        appointment_date=date,
        start_time=start_time,
        end_time=end_time,
        status='PENDING',
        booking_notes=booking_notes
    )
    
    EmployeeAvailability.objects.create(
        employee=employee,
        date=date,
        start_time=start_time,
        end_time=end_time,
        status='BOOKED'
    )
    
    # Send Notifications via signals or direct calls
    try:
        from apps.notifications.services import send_notification
        send_notification(
            user=customer.user,
            title="Appointment Confirmed",
            message=f"Your appointment at {salon.name} for {service.name} has been booked on {date} at {start_time}."
        )
        send_notification(
            user=employee.user,
            title="New Appointment Assigned",
            message=f"You have been assigned a new appointment for {service.name} on {date} at {start_time}."
        )
        send_notification(
            user=salon.manager.user,
            title="New Appointment Booked",
            message=f"A new appointment has been booked at {salon.name} for {service.name} on {date} at {start_time}."
        )
    except Exception:
        # Ignore notifications failures in tests or environments where it isn't configured
        pass
    
    return appointment

@transaction.atomic
def cancel_appointment(appointment, cancel_reason):
    if appointment.status in ['CANCELLED', 'COMPLETED']:
        raise ValidationError("Cannot cancel a completed or already cancelled appointment.")
        
    appointment.status = 'CANCELLED'
    appointment.cancel_reason = cancel_reason
    appointment.save()
    
    EmployeeAvailability.objects.filter(
        employee=appointment.employee,
        date=appointment.appointment_date,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        status='BOOKED'
    ).delete()
    
    try:
        from apps.notifications.services import send_notification
        send_notification(
            user=appointment.customer.user,
            title="Appointment Cancelled",
            message=f"Your appointment at {appointment.salon.name} on {appointment.appointment_date} has been cancelled."
        )
        send_notification(
            user=appointment.employee.user,
            title="Appointment Cancelled",
            message=f"The appointment on {appointment.appointment_date} at {appointment.start_time} has been cancelled."
        )
        send_notification(
            user=appointment.salon.manager.user,
            title="Appointment Cancelled",
            message=f"An appointment at {appointment.salon.name} on {appointment.appointment_date} has been cancelled."
        )
    except Exception:
        pass
    
    return appointment

def update_appointment_status(appointment, status):
    valid_statuses = ['CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'NO_SHOW', 'DECLINED']
    if status not in valid_statuses:
        raise ValidationError(f"Invalid status transition to {status}.")

    if appointment.status == 'CANCELLED' or appointment.status == 'DECLINED':
        raise ValidationError("Cannot change the status of a cancelled or declined appointment.")

    appointment.status = status
    appointment.save()

    # No further action for these states
    if status == 'NO_SHOW':
        # Free up the slot (no-show frees the availability just like a completed)
        EmployeeAvailability.objects.filter(
            employee=appointment.employee,
            date=appointment.appointment_date,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status='BOOKED'
        ).delete()
        # (optional) notify manager? Not required.
        return appointment

    if status in ['COMPLETED', 'DECLINED']:
        # Free up the slot regardless (completed or declined frees availability)
        EmployeeAvailability.objects.filter(
            employee=appointment.employee,
            date=appointment.appointment_date,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status='BOOKED'
        ).delete()

    try:
        from apps.notifications.services import send_notification
        if status == 'CONFIRMED':
            send_notification(
                user=appointment.customer.user,
                title="Appointment Confirmed",
                message=f"Your appointment at {appointment.salon.name} for {appointment.service.name} is confirmed."
            )
            if hasattr(appointment.salon, 'manager'):
                send_notification(
                    user=appointment.salon.manager.user,
                    title="Appointment Confirmed",
                    message=f"The appointment at {appointment.salon.name} for {appointment.service.name} has been confirmed."
                )
        elif status == 'DECLINED':
            send_notification(
                user=appointment.customer.user,
                title="Appointment Declined",
                message=f"Unfortunately, your appointment at {appointment.salon.name} for {appointment.service.name} on {appointment.appointment_date} at {appointment.start_time} has been declined. Please book another time."
            )
        elif status == 'COMPLETED':
            send_notification(
                user=appointment.customer.user,
                title="Appointment Completed",
                message=f"Thank you for visiting {appointment.salon.name}! Your appointment has been marked as completed."
            )
            if hasattr(appointment.salon, 'manager'):
                send_notification(
                    user=appointment.salon.manager.user,
                    title="Appointment Completed",
                    message=f"An appointment at {appointment.salon.name} for {appointment.service.name} has been completed."
                )
    except Exception:
        # Ignore notification failures
        pass

    return appointment
