# Id: base_model.py 202305 12/05/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada 
#   Rev: 202305
#   Date: 12/05/2023
#
# License description...

from pydantic import BaseModel as PyDantiModel
from sqlalchemy.orm import declarative_base

BaseModel = declarative_base()

#
# class SqlBaseModel(BaseModel):
#     __abstract__ = True
#
#     def update(
#         self,
#         model: PyDantiModel,
#         exclude=None,
#         exclude_none=True,
#         exclude_unset=False,
#     ):
#         for field, value in model.model_dump(
#             exclude=exclude, exclude_none=exclude_none, exclude_unset=exclude_unset
#         ).items():
#             setattr(self, field, value)
