from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.start_focus_session, name='start_focus'),
    path('end/', views.end_focus_session, name='end_focus'),
    path('status/', views.focus_status, name='focus_status'),
    path('end_session/<int:session_id>/', views.end_session, name='end_session'),
]
