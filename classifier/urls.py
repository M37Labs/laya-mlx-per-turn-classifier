from django.urls import path

from . import views

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("demo/", views.demo, name="demo"),
    path("api/status", views.api_status, name="api_status"),
    path("api/classify", views.api_classify, name="api_classify"),
]
