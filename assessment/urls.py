from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:token>/', views.assessment_test, name='assessment_test'),
    path('<uuid:token>/start/', views.start_test, name='start_test'),
    path('<uuid:token>/take/', views.take_test, name='take_test'),
]