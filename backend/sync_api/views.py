from __future__ import annotations

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
            return Response({"detail": str(e)}, status=403)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)

        return Response({})
