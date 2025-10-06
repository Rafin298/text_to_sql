from django.urls import path
from .views import Text2SQLAPIView

urlpatterns = [
    path("api/text2sql/", Text2SQLAPIView.as_view(), name="text2sql"),
]