from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sync_api.jwt import POWERSYNC_URL, mint_powersync_token, powersync_jwks_k
from sync_api.mutations import Mutation, dispatch_mutations_sync


class SyncTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = mint_powersync_token(request.user.user_id)
        return Response({"token": token, "powersync_url": POWERSYNC_URL})


class SyncJwksView(APIView):
    """JWKS for HS256 local dev (PowerSync config can also embed keys inline)."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "keys": [
                    {
                        "kty": "oct",
                        "k": powersync_jwks_k(),
                        "alg": "HS256",
                        "kid": "inventory-local-key",
                        "use": "sig",
                    }
                ]
            }
        )


class SyncMutationsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mutations_raw = request.data.get("mutations") if isinstance(request.data, dict) else None
        if not isinstance(mutations_raw, list) or len(mutations_raw) == 0:
            return Response({})

        mutations = [
            Mutation(
                op=str(m.get("op", "")),
                type=str(m.get("type", "")),
                data=m.get("data") or {},
            )
            for m in mutations_raw
            if isinstance(m, dict)
        ]

        try:
            dispatch_mutations_sync(request.user.user_id, mutations)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({})


class SyncWriteCheckpointProxyView(APIView):
    """Proxy write-checkpoint through Django so browser clients get /api CORS on ngrok."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        client_id = (request.query_params.get("client_id") or "").strip()
        if not client_id:
            return Response({"detail": "client_id required"}, status=status.HTTP_400_BAD_REQUEST)

        auth = (request.headers.get("Authorization") or "").strip()
        if not auth:
            return Response({"detail": "Authorization required"}, status=status.HTTP_401_UNAUTHORIZED)

        target = f"{POWERSYNC_URL.rstrip('/')}/write-checkpoint2.json?client_id={client_id}"
        upstream = Request(target, headers={"Authorization": auth})
        try:
            with urlopen(upstream, timeout=15) as resp:
                payload = json.loads(resp.read().decode())
                return Response(payload, status=resp.status)
        except HTTPError as exc:
            body = exc.read().decode() if exc.fp else ""
            try:
                payload = json.loads(body) if body else {"detail": exc.reason}
            except json.JSONDecodeError:
                payload = {"detail": body or exc.reason}
            return Response(payload, status=exc.code)
        except URLError as exc:
            return Response(
                {"detail": f"PowerSync unreachable: {exc.reason}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
