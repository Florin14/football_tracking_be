from .base_schema import BaseSchema


class ConfirmationSchema(BaseSchema):
    message: str = "Process was successful!"
