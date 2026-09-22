from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Laya Decision Engine: administration"
admin.site.site_title = "Laya admin"
admin.site.index_title = "Use cases & demo content"
admin.site.site_url = "/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("classifier.urls")),
]
