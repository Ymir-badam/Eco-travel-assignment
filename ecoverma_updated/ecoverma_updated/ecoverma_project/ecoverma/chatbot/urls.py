from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = "chatbot"


urlpatterns = [
    path("", views.home, name="home"),
    path("chat/", views.chat, name="chat"),
    path("chat/new/", views.new_conversation, name="new_conversation"),
    path("chat/<int:conversation_id>/", views.chat, name="chat_detail"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/carbon/", views.carbon_api, name="carbon_api"),

    path("signup/", views.signup, name="signup"),
    path("privacy/", views.privacy, name="privacy"),
    path("consent/", views.consent, name="consent"),
    path("privacy/delete-conversations/", views.delete_my_conversations, name="delete_conversations"),
    path("privacy/delete-account/", views.delete_account, name="delete_account"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="chatbot/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="chatbot:home"),
        name="logout",
    ),
]
