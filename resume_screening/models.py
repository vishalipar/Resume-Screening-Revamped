from django.db import models
from resume_parser.models import JobRole

# Create your models here.

class UserInfo(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    score = models.IntegerField()
    skills = models.JSONField(default=list)
    resume = models.FileField(upload_to='resumes/')
    status = models.BooleanField(default=False)
    job_role = models.ForeignKey(JobRole, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return self.name