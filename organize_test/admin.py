from django.contrib import admin
from .models import Position, newTest, Question, QuestionOption, QuestionModel
# Register your models here.

admin.site.register(Position)
admin.site.register(newTest)
admin.site.register(Question)
admin.site.register(QuestionOption)
admin.site.register(QuestionModel)