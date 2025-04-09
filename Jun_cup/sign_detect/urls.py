from django.urls import path
from . import views

urlpatterns = [
    path('', views.sign_detect, name='sign_detect')
]
