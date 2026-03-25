"""
URL configuration for focus_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from core.views import landing, dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name='landing'),
    path('dashboard/', dashboard, name='dashboard'),
    path('users/', include('users.urls')),
    path('courses/', include('courses.urls')),
    path('focus/', include('focus.urls')),
    path('study/', include('study.urls')),
    path('videos/', include('videos.urls')),
    path('tracking/', include('tracking.urls')),
    path('api/', include('ai_engine.urls')),  # AI Engine API endpoints
]

