from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import CurrentUser, get_current_user
from app.sync.jwt import mint_powersync_token, powersync_jwks_k
from app.sync.mutations import Mutation, dispatch_mutations
from app.config import get_settings

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncTokenResponse(BaseModel):
    token: str
    powersync_url: str


class MutationPayload(BaseModel):
    op: str = ""
    type: str = ""
    data: dict[str, Any] | None = None


class MutationsRequest(BaseModel):
    mutations: list[MutationPayload] | None = None


@router.post("/token/", response_model=SyncTokenResponse)
def sync_token(user: CurrentUser = Depends(get_current_user)) -> SyncTokenResponse:
    settings = get_settings()
    return SyncTokenResponse(
        token=mint_powersync_token(user.user_id),
        powersync_url=settings.powersync_url,
    )


@router.get("/jwks/")
def sync_jwks() -> dict[str, Any]:
    settings = get_settings()
    return {
        "keys": [
            {
                "kty": "oct",
                "k": powersync_jwks_k(),
                "alg": "HS256",
                "kid": settings.powersync_jwt_kid,
                "use": "sig",
            }
        ]
    }


@router.post("/mutations/")
async def sync_mutations(
    body: MutationsRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    mutations_raw = body.mutations
    if not mutations_raw:
        return {}

    mutations = [
        Mutation(
            op=m.op,
            type=m.type,
            data=m.data or {},
        )
        for m in mutations_raw
    ]

    try:
        await dispatch_mutations(user.user_id, mutations)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {}
