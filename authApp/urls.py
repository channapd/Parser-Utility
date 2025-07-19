from django.urls import path
from . import views

app_name="authApp"
urlpatterns = [
    path("login", views.login, name="login"),
    path("register", views.register, name="register"),
    path("admin_register", views.admin_register, name="admin_register"),
    path("logout/", views.logout_user, name="logout"),
]
