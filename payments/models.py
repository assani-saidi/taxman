from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta

PAYMENT_STATUSES = [
    ('pending', 'Pending'),
    ('success', 'Success'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]

PAYMENT_TYPES = [
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('annually', 'Annually'),
]


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_plan = models.ForeignKey("PaymentPlan", on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    identity = models.CharField(max_length=100)
    period = models.CharField(max_length=100, choices=PAYMENT_TYPES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default='pending')
    internal_reference = models.CharField(max_length=100)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.user} on {self.valid_from} to {self.valid_to}"

    def mark_as_completed(self, payment_reference):
        """
        Mark payment as completed and set validity period from today
        """
        self.status = 'success'
        self.payment_reference = payment_reference

        # Set valid_from to today
        today = timezone.now().date()
        self.valid_from = today

        # Calculate valid_to based on period
        if self.period == 'monthly':
            self.valid_to = today + relativedelta(months=1)
        elif self.period == 'quarterly':
            self.valid_to = today + relativedelta(months=3)
        elif self.period == 'annually':
            self.valid_to = today + relativedelta(years=1)
        else:
            # Default to annual if somehow invalid period
            self.valid_to = today + relativedelta(years=1)

        self.save()

    def mark_as_failed(self):
        """
        Mark payment as failed
        """
        self.status = 'failed'
        self.save()

    def is_active(self):
        """
        Check if payment is currently active (successful and within validity period)
        """
        today = timezone.now().date()
        return (
                self.status == 'success' and
                self.valid_from <= today <= self.valid_to
        )

    def days_until_expiry(self):
        """
        Calculate days until payment expires
        """
        if self.status != 'success':
            return None

        today = timezone.now().date()
        if today > self.valid_to:
            return 0  # Already expired

        return (self.valid_to - today).days


class PaymentPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    period = models.CharField(max_length=100, choices=PAYMENT_TYPES, default='annually')
    currency = models.CharField(max_length=5, default='USD')
    includes = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_period_display()})"

    @property
    def payment_period(self):
        return "USD / Year" if self.period == "annually" else f"USD / {self.get_period_display()[:-2]}"
