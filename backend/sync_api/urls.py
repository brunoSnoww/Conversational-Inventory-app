from django.urls import path

from sync_api.views import SyncJwksView, SyncMutationsView, SyncTokenView, SyncWriteCheckpointProxyView

urlpatterns = [
    path("token/", SyncTokenView.as_view()),
    path("mutations/", SyncMutationsView.as_view()),
    path("jwks/", SyncJwksView.as_view()),
    path("write-checkpoint/", SyncWriteCheckpointProxyView.as_view(), name="sync-write-checkpoint"),
]
