import django_fsm as fsm
from cuid2 import Cuid
from django.conf import settings
from django.db import models

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class Application(fsm.FSMModelMixin, models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    state = fsm.FSMField(default="draft", protected=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    project_title = models.CharField(max_length=255)
    company_no = models.CharField(max_length=255)
    incorporation_date = models.DateField()
    contact_person = models.CharField(max_length=255)
    telephone = models.CharField(max_length=255)
    business_nature = models.CharField(max_length=255)
    business_location = models.CharField(max_length=255)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012

    def __str__(self):
        return self.project_title

    @fsm.transition(field=state, source="draft", target="submitted")
    def submit(self, **kwargs):
        """
        This function may contain side effects,
        like updating caches, notifying users, etc.
        The return value will be discarded.
        """
        #  We will create a task manager here to prevent one person handling multiple submissions simultaneously.
