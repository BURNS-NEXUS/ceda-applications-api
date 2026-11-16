def check_is_email(email: str) -> bool:
    """Validate email format."""
    return "@" in email and "." in email.split("@")[1]
