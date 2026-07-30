from django.urls import path
from .views import StartConversationView, MyConversationsView, ConversationMessagesView

urlpatterns = [
    path("start/", StartConversationView.as_view(), name="start-conversation"),
    path("mine/", MyConversationsView.as_view(), name="my-conversations"),
    path("<uuid:conversation_id>/messages/", ConversationMessagesView.as_view(), name="conversation-messages"),
]