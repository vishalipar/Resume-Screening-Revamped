"""
URL configuration for resume_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from chat_bot.views import ChatView
from resume_parser.views import JobRoleView, job_roles_view, JobRolesAPIView
from resume_screening.views import CustomLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        CustomLoginView.as_view(),
        name="login",
    ),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('resume_screening.urls')),
    path('assessment-test/', include('assessment.urls')),
    path('api/chat/', ChatView.as_view(), name='chat'),
    path('api/jobs/', JobRoleView.as_view(), name='jobs'),
    
    path('job-roles/', job_roles_view, name='job_roles'),
    path('api/job-roles/', JobRolesAPIView.as_view(), name='job_roles_api'),
    path('api/job-roles/<int:job_id>/update/', JobRolesAPIView.as_view(), name='job_update'),
    path('api/job-roles/<int:job_id>/delete/', JobRolesAPIView.as_view(), name='job_delete'),
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
