"""Sector inference and reviewer expertise matching for evaluation tasks.

Applications carry free-text ``business_nature`` and ``project_title`` fields,
so we infer a coarse sector from keywords. Reviewers store explicit
``expertise_sectors`` slugs on their user record. An empty list means the
reviewer is willing to assess any sector.
"""

SECTOR_LABELS = {
    "energy": "Energy & renewables",
    "agriculture": "Agriculture & food",
    "fintech": "Financial services",
    "health": "Health & life sciences",
    "logistics": "Logistics & infrastructure",
    "manufacturing": "Manufacturing & industry",
    "ict": "ICT & software",
    "general": "General",
}

SECTOR_KEYWORDS = {
    "energy": (
        "solar", "renewable", "energy", "power", "electric", "battery",
        "irrigation", "wind", "hydro", "grid",
    ),
    "agriculture": (
        "agricultur", "farm", "livestock", "crop", "agri", "food production",
        "aquaculture", "fishing", "beekeeping",
    ),
    "fintech": (
        "fintech", "financial", "banking", "payment", "insurance", "lending",
        "credit", "loan", "investment",
    ),
    "health": (
        "health", "medical", "pharma", "clinic", "diagnostic", "wellness",
        "hospital", "biotech",
    ),
    "logistics": (
        "logistic", "cold storage", "transport", "freight", "warehouse",
        "supply chain", "delivery", "distribution",
    ),
    "manufacturing": (
        "manufactur", "factory", "industrial", "fabrication", "processing",
        "production line",
    ),
    "ict": (
        "software", "digital", "platform", "app", "data", "cyber", "cloud",
        "telecom", "artificial intelligence", "analytics",
    ),
}


def sector_for_text(*values):
    """Return the first matching sector slug for the given free-text values."""
    text = " ".join(str(value or "") for value in values).lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return sector
    return "general"


def sector_for_application(application):
    return sector_for_text(
        getattr(application, "project_title", ""),
        getattr(application, "business_nature", ""),
    )


def sectors_for_user(user):
    """Normalise a reviewer's stored expertise slugs."""
    values = getattr(user, "expertise_sectors", None) or []
    return {str(value).strip().lower() for value in values if str(value).strip()}


def matches_expertise(user, sector):
    """An empty expertise list means the reviewer accepts any sector."""
    expertise = sectors_for_user(user)
    return not expertise or sector in expertise
