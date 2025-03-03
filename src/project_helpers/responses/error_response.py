# Id: error_response.py 202307 04/07/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada 
#   Rev: 202307
#   Date: 04/07/2023
#
# License description...
from fastapi.responses import JSONResponse
from ..error import Error


class ErrorResponse(JSONResponse):
    def __init__(self, error: Error, statusCode=500, message=None, fields=None):
        e = error.value
        e.fields = fields
        e.message = message if message else e.message
        super().__init__(content=e.dict(), status_code=statusCode)