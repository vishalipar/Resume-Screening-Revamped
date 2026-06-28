from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('candidates/', views.candidates, name='candidates'),
    path('delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('send-email/', views.send_email_view, name='send_email'),
    path('export/', views.export_candidates, name='export_candidates'),
    path('schedule-interviews/', views.schedule_interviews, name='schedule_interviews'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('test/', include('organize_test.urls')),
]