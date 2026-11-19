from django.db.models import QuerySet
from ninja import Schema
from pydantic import Field


class TaskFilters(Schema):
    skip: int = Field(default=0, ge=0)
    take: int | None = Field(default=None, ge=0)
    task_type: str | None = None
    status: str | None = None
    application_id: str | None = None
    assignee_id: str | None = None
    unassigned: bool | None = None

    def apply(self, tasks: QuerySet) -> QuerySet:
        if self.task_type is not None:
            tasks = tasks.filter(task_type=self.task_type)
        if self.status is not None:
            tasks = tasks.filter(status=self.status)
        if self.application_id is not None:
            tasks = tasks.filter(application_id=self.application_id)
        if self.assignee_id is not None:
            tasks = tasks.filter(
                assignments__employee_id=self.assignee_id,
                assignments__is_active=True,
            )
        if self.unassigned is not None:
            if self.unassigned:
                tasks = tasks.exclude(assignments__is_active=True)
            else:
                tasks = tasks.filter(assignments__is_active=True)
        return tasks.distinct()
