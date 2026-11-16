from ninja import Schema


class ApplicationOut(Schema):
    id: str
    project_title: str


class ApplicationIn(Schema):
    project_title: str
