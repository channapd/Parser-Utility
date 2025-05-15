from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

app_name = "mainApp"
urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload_and_convert, name="upload_and_convert"),
    path('download/<str:file_type>/<int:upload_id>/', views.download_file, name='download_file'),
    path("user-management/", views.user_management, name="user_management"),
    path('admin-home/', views.admin_home, name='admin_home'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
