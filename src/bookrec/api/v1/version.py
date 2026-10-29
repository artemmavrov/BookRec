from importlib.metadata import version as package_version

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

APP_VERSION = package_version("bookrec")


@router.get("/version")
async def get_version() -> dict[str, str]:
    return {"version": APP_VERSION}
