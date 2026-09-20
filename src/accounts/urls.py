from django.contrib.auth import views as auth_views
from django.urls import path

from collect.throttle import throttle

from .views import SignUpView


urlpatterns = [
    path(
        "signup/",
        throttle("signup", "THROTTLE_SIGNUP")(SignUpView.as_view()),
        name="signup",
    ),
    # Rate limited login, to make password guessing impractical. This app is
    # included before `django.contrib.auth.urls` (see `collect.urls`), so this
    # is the view that answers `/accounts/login/`, while `auth:login` keeps
    # reversing to the same address.
    path(
        "login/",
        throttle("login", "THROTTLE_LOGIN")(auth_views.LoginView.as_view()),
        name="login",
    ),
]
