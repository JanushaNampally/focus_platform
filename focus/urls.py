from django.urls import path
from .views import timer, complete_session

urlpatterns = [
    path('timer/', timer, name='timer'),
    path('complete/', complete_session, name='complete_session'),
]