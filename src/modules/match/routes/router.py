from fastapi import APIRouter

router = APIRouter(prefix='/matches', tags=['Match'])

emailRouter = APIRouter(prefix='/email', tags=['Email'])
