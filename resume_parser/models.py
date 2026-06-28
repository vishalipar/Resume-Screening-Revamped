from django.db import models

class JobRole(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    required_skills = models.JSONField(default=list)
    experience_required = models.IntegerField(default=0)
    education_level = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=255, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'),
        ('closed', 'Closed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title


class Resume(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    skills = models.JSONField(default=list)
    experience_years = models.IntegerField(default=0)
    resume_text = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name