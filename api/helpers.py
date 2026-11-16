def check_is_email(value: str) -> bool:
    import re

    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(email_regex, value) is not None
