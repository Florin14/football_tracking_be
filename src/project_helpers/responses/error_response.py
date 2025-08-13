from fastapi.responses import JSONResponse
from ..error import Error


class ErrorResponse(JSONResponse):
    def __init__(self, error: Error, statusCode=500, message=None, fields=None):
        e = error.value
        e.fields = fields
        e.message = message if message else e.message
        super().__init__(content=e.dict(), status_code=statusCode)