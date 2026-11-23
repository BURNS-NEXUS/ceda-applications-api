from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from pydantic import Field

from .models import ProgrammeCall

router = Router()


class CallFields(Schema):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    eligibility: str = Field(min_length=1)
    required_documents: str = Field(min_length=1)
    opens_on: date
    closes_on: date


class CallOut(CallFields):
    id: int
    status: str
    has_brief: bool


class EntryOut(Schema):
    id: str
    project_title: str
    state: str
    email: str


def require_manager(request):
    if not request.user.has_perm("api.change_systemsettings"):
        raise HttpError(403, "Programme management permission required.")


def visible_calls(request):
    rows = ProgrammeCall.objects.defer("brief")
    return rows if request.user.has_perm("api.change_systemsettings") else rows.filter(published=True)


def serialize(call):
    return {**{name: getattr(call, name) for name in CallFields.model_fields},
            "id": call.pk, "status": call.status, "has_brief": call.has_brief}


@router.get("/", response=list[CallOut])
def list_calls(request):
    return [serialize(call) for call in visible_calls(request).order_by("-opens_on", "-id")]


@router.post("/", response={201: CallOut})
def create_call(request, fields: Form[CallFields], brief: File[UploadedFile] = None):
    require_manager(request)
    if fields.closes_on < fields.opens_on:
        raise HttpError(422, "Deadline must be on or after the opening date.")
    content = b""
    if brief:
        if brief.size > 3 * 1024 * 1024:
            raise HttpError(422, "Choose a PDF of 3 MB or less.")
        content = brief.read()
        if not content.startswith(b"%PDF-"):
            raise HttpError(422, "The brief must be a PDF.")
    call = ProgrammeCall.objects.create(**fields.model_dump(), brief=content, has_brief=bool(content))
    return 201, serialize(call)


@router.post("/{call_id}/publish", response=CallOut)
def publish_call(request, call_id: int):
    require_manager(request)
    call = get_object_or_404(ProgrammeCall.objects.defer("brief"), pk=call_id)
    call.published = True
    call.save(update_fields=["published"])
    return serialize(call)


@router.get("/{call_id}/brief")
def download_brief(request, call_id: int):
    call = get_object_or_404(visible_calls(request), pk=call_id, has_brief=True)
    response = HttpResponse(bytes(call.brief), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="programme-brief.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


@router.get("/{call_id}/applications", response=list[EntryOut])
def call_applications(request, call_id: int):
    require_manager(request)
    call = get_object_or_404(ProgrammeCall, pk=call_id)
    return call.applications.order_by("-created_at")
