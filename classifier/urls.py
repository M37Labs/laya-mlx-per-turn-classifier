from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/status", views.api_status, name="api_status"),
    path("api/classify", views.api_classify, name="api_classify"),
]
