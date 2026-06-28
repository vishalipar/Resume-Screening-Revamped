from django.urls import path
from . import views

urlpatterns = [
    path('', views.organize_test, name='organize_test'),
    path('add_question/', views.add_question, name='add_question'),
    path('manage_test/<int:test_id>', views.manage_test, name='manage_test'),
    path('generate-questions/', views.GenerateQuestionsAPI.as_view(), name='generate-questions'),
    path('save-questions/', views.SaveQuestionsAPI.as_view(), name='save-questions'),
    path('delete-question/', views.DeleteQuestionAPI.as_view(), name='delete-question'),
    path('update-questions/', views.UpdateQuestionsAPI.as_view(), name='update-questions'),
    path('toggle-question/', views.toggle_question, name='toggle_question'),
    path('delete-test/<int:id>/', views.delete_test, name='delete_test'),
    path('send-emails/', views.send_emails, name='send_emails'),
    path('result/<int:attempt_id>/', views.result_api, name='result_api')
]