from django.urls import path
from .views import home, onboarding, success

urlpatterns = [
    path('', home, name = 'home'),
    path('onboarding/', onboarding, name='onboarding'),
    path('success/', success, name='success'),
]