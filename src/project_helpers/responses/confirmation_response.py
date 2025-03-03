# Id: confirmation_response.py 202307 12/07/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada
#   Rev: 202307
#   Date: 12/07/2023
#
# License description...
from pydantic import BaseModel, Field


class ConfirmationResponse(BaseModel):
    message: str = Field("Process was succesful", example="Process was succesful")
