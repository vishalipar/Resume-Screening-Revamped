from django.db import models
from organize_test.models import newTest
from organize_test.models import QuestionModel
import uuid
from django.utils import timezone
# Create your models here.

class TestAttempt(models.Model):
    test = models.ForeignKey(newTest, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    score = models.IntegerField(default=0)
    status = models.CharField(default='pending', max_length=20)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.email
        
class Answer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE)
    question = models.ForeignKey(QuestionModel, on_delete=models.CASCADE, related_name="responses")
    selected_answer = models.TextField(null=True, blank=True)