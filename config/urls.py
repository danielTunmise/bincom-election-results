"""Project URLs: everything is handled by the `elections` app."""
from django.urls import include, path

urlpatterns = [
    path("", include("elections.urls")),
]
