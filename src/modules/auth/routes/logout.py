from fastapi import Depends
from extensions.auth_jwt import AuthJWT
from sqlalchemy.orm import Session
from extensions import get_db
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("/logout", response_model=ConfirmationResponse)
def logout(auth: AuthJWT = Depends(), db: Session = Depends(get_db)):
    auth.jwt_required()
    db.commit()
    auth.unset_jwt_cookies()
    return ConfirmationResponse()
