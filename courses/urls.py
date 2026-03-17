from django.urls import path
from .views import course_detail   # ADD THIS LINE

urlpatterns = [
    path('<int:course_id>/', course_detail, name='course_detail'),
]
