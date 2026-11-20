from .models import DocumentType


def document_upload_progress(application):
    uploaded = {
        document.document_type_id: document for document in application.documents.all()
    }
    data = []
    missing_required = []

    for document_type in DocumentType.objects.filter(is_active=True):
        document = uploaded.get(document_type.id)
        if document_type.is_required and document is None:
            missing_required.append(document_type.name)
        data.append(
            {
                "id": document_type.id,
                "name": document_type.name,
                "description": document_type.description,
                "allowed_file_types": document_type.allowed_file_types,
                "is_required": document_type.is_required,
                "is_active": document_type.is_active,
                "uploaded": document is not None,
                "document_id": document.id if document else None,
                "status": document.status if document else None,
                "application_type": document_type.application_type,
            }
        )

    return {
        "total": len(data),
        "data": data,
        "all_required_uploaded": not missing_required,
        "missing_required": missing_required,
    }
