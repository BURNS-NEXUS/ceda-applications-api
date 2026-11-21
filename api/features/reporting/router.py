import csv
import io
from datetime import date

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from .models import ReportTemplate
from .schemas import (
    DashboardKPIs,
    PipelineReport,
    ProcessingTimeReport,
    ReportFilters,
    ReportTemplateIn,
    ReportTemplateOut,
    ScoringSummaryReport,
    StatusBreakdownRow,
)
from .services import (
    audit_trail,
    dashboard_kpis,
    export_rows,
    pipeline_summary,
    processing_time_summary,
    reviewer_workload,
    scoring_summary_report,
    stalled_applications,
    status_breakdown,
)

router = Router()

PERM_VIEW_REPORTS = "reporting.view_reports"
PERM_MANAGE_TEMPLATES = "reporting.manage_report_templates"


def _require_perm(request, permission):
    if not request.auth.has_perm(permission):
        raise HttpError(403, "You do not have permission to perform this action.")


def _has_perm(request, permission):
    return bool(request.auth and request.auth.has_perm(permission))


def _filters_from_query(filters: ReportFilters):
    return {
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "status_in": filters.status_in,
        "status_not_in": filters.status_not_in,
        "search": filters.search,
    }


@router.get("/reports/pipeline", response=PipelineReport)
def get_pipeline_report(request, filters: Query[ReportFilters]):
    _require_perm(request, PERM_VIEW_REPORTS)
    return pipeline_summary(**_filters_from_query(filters))


@router.get("/reports/status-breakdown", response=list[StatusBreakdownRow])
def get_status_breakdown(request, filters: Query[ReportFilters]):
    _require_perm(request, PERM_VIEW_REPORTS)
    return status_breakdown(**_filters_from_query(filters))


@router.get("/reports/processing-time", response=ProcessingTimeReport)
def get_processing_time(request, filters: Query[ReportFilters]):
    _require_perm(request, PERM_VIEW_REPORTS)
    return processing_time_summary(**_filters_from_query(filters))


@router.get("/reports/reviewer-workload")
def get_reviewer_workload(request):
    _require_perm(request, PERM_VIEW_REPORTS)
    return reviewer_workload()


@router.get("/reports/scoring-summary", response=ScoringSummaryReport)
def get_scoring_summary(request, filters: Query[ReportFilters]):
    _require_perm(request, PERM_VIEW_REPORTS)
    return scoring_summary_report(**_filters_from_query(filters))


@router.get("/reports/dashboard", response=DashboardKPIs)
def get_dashboard(request, filters: Query[ReportFilters]):
    _require_perm(request, PERM_VIEW_REPORTS)
    return dashboard_kpis(**_filters_from_query(filters))


@router.get("/reports/stalled")
def get_stalled(request, days: int = 7, filters: Query[ReportFilters] = None):
    _require_perm(request, PERM_VIEW_REPORTS)
    f = _filters_from_query(filters) if filters else {}
    return stalled_applications(days=days, **f)


@router.get("/reports/audit-trail")
def get_audit_trail(request, date_from: date = None, date_to: date = None, resource_type: str = None, limit: int = 100):
    _require_perm(request, PERM_VIEW_REPORTS)
    from datetime import date as _date

    return audit_trail(date_from=date_from, date_to=date_to, resource_type=resource_type, limit=limit)


@router.get("/reports/export")
def export_report(request, filters: Query[ReportFilters], format: str = "csv"):
    _require_perm(request, PERM_VIEW_REPORTS)
    if format != "csv":
        raise HttpError(400, "Only csv export is supported.")
    rows = export_rows(**_filters_from_query(filters))
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="applications_report.csv"'
    return response


@router.get("/reports/templates", response=list[ReportTemplateOut])
def list_templates(request):
    _require_perm(request, PERM_VIEW_REPORTS)
    return [
        ReportTemplateOut(
            id=t.id,
            name=t.name,
            description=t.description,
            filters=t.filters or {},
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in ReportTemplate.objects.all()
    ]


@router.post("/reports/templates", response={201: ReportTemplateOut})
@csrf_exempt
def create_template(request, payload: ReportTemplateIn):
    _require_perm(request, PERM_MANAGE_TEMPLATES)
    template = ReportTemplate.objects.create(
        name=payload.name,
        description=payload.description,
        filters=payload.filters,
        created_by=request.auth,
    )
    return 201, ReportTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        filters=template.filters or {},
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/reports/templates/{template_id}", response={200: dict})
@csrf_exempt
def delete_template(request, template_id: str):
    _require_perm(request, PERM_MANAGE_TEMPLATES)
    try:
        template = ReportTemplate.objects.get(id=template_id)
    except ReportTemplate.DoesNotExist:
        raise HttpError(404, "Template not found")
    template.delete()
    return {"success": True}