from project_helpers.schemas import BaseSchema, FilterSchema


class UserAdd(BaseSchema):
    pass


class UserFilter(FilterSchema):
    sortBy: str = "companyName"