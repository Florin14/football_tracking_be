# from datetime import datetime
#
# import requests
# from fastapi import Depends
# from sqlalchemy.orm import Session
# from extensions import get_db
# from project_helpers.config import recaptcha
# from project_helpers.error import Error
# from project_helpers.exceptions import ErrorException
# from ...models import LoginAttemptModel, LoginBody
#
#
# class VerifyRecaptcha:
#     @staticmethod
#     def _verify_recaptcha_token(token: str):
#         r = requests.post(recaptcha.RECAPTCHA_URL, data={"secret": recaptcha.RECAPTCHA_SECRET_KEY, "response": token})
#         r = r.json()
#         if r.get("success"):
#             return True
#         return False
#
#     def __call__(self, body: LoginBody, db: Session = Depends(get_db)):
#
#         baseQuery = db.query(LoginAttemptModel)
#
#         # delete expired login attempts
#         query = baseQuery.filter(LoginAttemptModel.exp < datetime.now())
#         query.delete(synchronize_session="fetch")
#         db.commit()
#
#         record = baseQuery.get(body.email)
#
#         if record is None:
#             record = LoginAttemptModel(email=body.email)
#             db.add(record)
#             db.flush()
#         if record.attempt == 0:
#             if body.recaptchaToken is None or not self._verify_recaptcha_token(body.recaptchaToken):
#                 raise ErrorException(error=Error.INVALID_CREDENTIALS_RECAPTCHA_TOKEN_IS_REQUIRED, statusCode=401)
#         else:
#             record.attempt = record.attempt - 1
#             db.commit()
