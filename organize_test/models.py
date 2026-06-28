from django.db import models

# Create your models here.

class Position(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.title

class newTest(models.Model):
    DIFFICULTY_CHOICES = {
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    }
    title = models.CharField(max_length=200)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    duration = models.IntegerField(help_text='Duration in minutes')
    passing_score = models.IntegerField(help_text='Passing score percentage')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
# manually create questions    
class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('coding', 'Coding'),
        ('descriptive', 'Descriptive'),
    ]
    
    DIFFICULTY_CHOICES =[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    question_text = models.TextField(help_text = 'Enter the question text')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    marks = models.IntegerField()
    # for coding questions
    expected_solution = models.TextField(blank=True, null=True, help_text='Sample solution for coding question')
    
    # For descriptive questions
    sample_answer = models.TextField(blank=True, null=True, help_text='Key points to be covered in answer')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.question_type.upper()} - {self.question_text[:50]}'
        
# For MCQ type questions
class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=400)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.option_text} ({'Correct' if self.is_correct else 'Wrong'})"
        
#ai generated questions
class QuestionModel(models.Model):
    test = models.ForeignKey(newTest, on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()
    options = models.JSONField(blank=True, null=True)  # for MCQ
    answer = models.TextField()
    is_selected = models.BooleanField(default=False)
    marks = models.IntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
