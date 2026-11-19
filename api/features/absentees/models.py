from cuid2 import Cuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class Absentee(models.Model):
    """A user who is absent from work / on leave.

    Only ``User`` records can be absentees. An employee has at most one
    absence record at a time; adding a new absence for a user replaces the
    previous one, while removing the record clears the absence.
    """

    class LeaveType(models.TextChoices):
        VACATION = "vacation", "Vacation"
        SICK = "sick", "Sick leave"
        PERSONAL = "personal", "Personal leave"
        UNPAID = "unpaid", "Unpaid leave"
        OTHER = "other", "Other"

    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="absentees",
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices,
        default=LeaveType.VACATION,
    )
    start_date = models.DateField()
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text="Leave end date; null means the leave is open-ended.",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        verbose_name = "Absentee"
        verbose_name_plural = "Absentees"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["user"],
                name="unique_absentee_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.get_leave_type_display()}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(
                {"end_date": "End date cannot be before the start date."}
            )

    @property
    def is_on_leave(self):
        """Whether the user is on leave on today's date."""
        today = timezone.localdate()
        end_date = self.end_date or today
        return self.start_date <= today <= end_date
