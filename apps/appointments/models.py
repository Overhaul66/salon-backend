import uuid
from django.db import models
from apps.users.models import Customer, SalonEmployee
from apps.salons.models import Salon, SalonService

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('DECLINED', 'Declined'),
        ('NO_SHOW', 'No Show'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='appointments')
    employee = models.ForeignKey(SalonEmployee, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(SalonService, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    booking_notes = models.TextField(blank=True, null=True)
    cancel_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointments'
        ordering = ['-appointment_date', '-start_time']

    def __str__(self):
        return f"Appointment: {self.customer.user.email} - {self.salon.name} ({self.appointment_date} {self.start_time})"
