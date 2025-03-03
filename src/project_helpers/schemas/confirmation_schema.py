# Id: confirmation_schema.py 202305 12/05/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada
#   Rev: 202305
#   Date: 12/05/2023
#
# License description...
from .base_schema import BaseSchema


class ConfirmationSchema(BaseSchema):
    message: str = "Process was successful!"
