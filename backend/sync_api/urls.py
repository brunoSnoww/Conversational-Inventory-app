from django.urls import path

from sync_api.views import SyncJwksView, SyncMutationsView, SyncTokenView

urlpatterns = [
    path("token/", SyncTokenView.as_view()),
    path("mutations/", SyncMutationsView.as_view()),
    path("jwks/", SyncJwksView.as_view()),
]
