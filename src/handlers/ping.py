"""API reachability, independent of database availability."""

from fastapi import APIRouter

from src.schemas.ping import PingResponse

router = APIRouter()


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    return PingResponse(status="ok")
