import uuid
from django.db import models
from apps.common.models import BaseModel
from apps.users.models import SalonManager

class Salon(BaseModel):
    GENDER_TYPE_CHOICES = (
        ('UNISEX', 'Unisex'),
        ('MEN_ONLY', 'Men Only'),
        ('WOMEN_ONLY', 'Women Only'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    )

    manager = models.OneToOneField(SalonManager, on_delete=models.CASCADE, related_name='salon')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    logo = models.ImageField(upload_to='salon_logos/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='salon_covers/', null=True, blank=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    gender_type = models.CharField(max_length=15, choices=GENDER_TYPE_CHOICES, default='UNISEX')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'salons'

    def __str__(self):
        return self.name


class SalonImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='salon_gallery/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        db_table = 'salon_images'

    def __str__(self):
        return f"Gallery image for {self.salon.name}"


class ServiceCatalog(BaseModel):
    CATEGORY_CHOICES = (
        ('MEN', 'Men'),
        ('WOMEN', 'Women'),
        ('UNISEX', 'Unisex'),
    )

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='UNISEX')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']
        db_table = 'service_catalog'

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class SalonService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='services')
    catalog_item = models.ForeignKey(ServiceCatalog, on_delete=models.PROTECT, related_name='salon_services', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_services'
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'catalog_item'],
                name='unique_salon_catalog_item',
                nulls_distinct=True,
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.salon.name}"


class SalonFavourite(BaseModel):
    customer = models.ForeignKey('users.Customer', on_delete=models.CASCADE, related_name='favourite_salons')
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='favourited_by')

    class Meta:
        db_table = 'salon_favourites'
        unique_together = ('customer', 'salon')

    def __str__(self):
        return f"{self.customer.user.email} favours {self.salon.name}"


class BusinessHours(models.Model):
    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='business_hours')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('salon', 'weekday')
        db_table = 'salon_business_hours'

    def __str__(self):
        return f"{self.get_weekday_display()} - {self.salon.name}"
