from django.urls import path

from accounts.views import register, login, logout, me, change_password

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login, name="login"),
    path("logout/", logout, name="logout"),
    path("me/", me, name="me"),
    path("change-password/", change_password, name="change-password"),
]
