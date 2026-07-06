from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import newTest, Position, Question, QuestionOption, QuestionModel
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import generate_questions
from django.http import JsonResponse
from django.db.models import Sum
from django.core.mail import send_mail
import json
from resume_screening.models import UserInfo
from assessment.models import TestAttempt, Answer
from resume_project.settings import EMAIL_HOST_USER
from django.utils.dateparse import parse_datetime
from django.utils import timezone

# Create your views here.

@login_required
def organize_test(request):
    if request.session.get('is_candidate'):
        return HttpResponse("Unauthorized access")

    newtest = newTest.objects.all()
    positions = Position.objects.all()
    shortlisted = UserInfo.objects.filter(status=True)
    attempts = TestAttempt.objects.select_related('test').order_by('-start_time')
    assigned_candidates = TestAttempt.objects.count()
    pending_tests = TestAttempt.objects.filter(status='pending').count()
    
    for a in attempts:
        total = QuestionModel.objects.filter(test=a.test, is_selected=True).aggregate(Sum('marks'))['marks__sum'] or 1
        a.percentage = (a.score / total) * 100
    
    if request.method == 'POST':
        title  = request.POST['title']
        position_id  = request.POST['position']
        level  = request.POST['level']
        duration  = request.POST['duration']
        passing_score  = request.POST['passing_score']
        test_description  = request.POST['description']
        
        try:
            position_obj = Position.objects.get(id=position_id)
            test = newTest.objects.create(
                title=title,
                position=position_obj,
                difficulty=level,
                duration=duration,
                passing_score=passing_score,
                description=test_description
            )

            return redirect('manage_test',test_id=test.id)
            
        except Position.DoesNotExist:
            pass
        
    context = {
        'newtest':newtest,
        'positions': positions,
        'shortlisted': shortlisted,
        'attempts': attempts,
        'assigned_candidates':assigned_candidates,
        'pending_tests':pending_tests,
    }
    return render(request, 'test.html', context)
    
@login_required
def add_question(request):
    if request.method == 'POST':
        type = request.POST['type']
        question = request.POST['question']
        difficulty = request.POST['difficulty']
        marks = request.POST['marks']
        
        question_obj = Question.objects.create(question_text=question, 
        question_type=type, 
        difficulty=difficulty, 
        marks=marks)
        
        if type == 'coding':
            expected_solution = request.POST.get('expected_solution', '')
            question_obj.expected_solution = expected_solution
            question_obj.save()
            
        elif type == 'descriptive':
            sample_answer = request.POST.get('sample_answer', '')
            question_obj.sample_answer = sample_answer
            question_obj.save()
            
        elif type == 'mcq':
            option_a = request.POST.get('option_a')
            option_b = request.POST.get('option_b')
            option_c = request.POST.get('option_c')
            option_d = request.POST.get('option_d')
            correct_answer = request.POST.get('correct_answer')
            
            QuestionOption.objects.create(
                question = question_obj,
                option_text = option_a,
                is_correct = (correct_answer == 'A')
            )
            QuestionOption.objects.create(
                question = question_obj,
                option_text = option_b,
                is_correct = (correct_answer == 'B')
            )
            QuestionOption.objects.create(
                question = question_obj,
                option_text = option_c,
                is_correct = (correct_answer == 'C')
            )
            QuestionOption.objects.create(
                question = question_obj,
                option_text = option_d,
                is_correct = (correct_answer == 'D')
            )
        
    return render(request, 'add_question.html')
    
@login_required
def manage_test(request, test_id):
    test = newTest.objects.get(id=test_id)
    questions = QuestionModel.objects.filter(test=test)

    selected_ids = questions.filter(is_selected=True).values_list('id', flat=True)

    context = {
        'test': test,
        'questions': questions,
        'selected_ids': list(selected_ids),
    }
    return render(request, 'manage_test.html', context)
    
class GenerateQuestionsAPI(APIView):
    def post(self, request):
        paragraph = request.data.get("paragraph")
        q_type = request.data.get("type")
        count = request.data.get("count")
        difficulty = request.data.get("difficulty")
        mcq_options = request.data.get("mcq_options")

        data = generate_questions(paragraph, q_type, count, difficulty, mcq_options)
        return Response({"questions": data})
        
class SaveQuestionsAPI(APIView):
    def post(self, request):
        questions = request.data.get("questions", [])
        test_id = request.data.get("test_id")
        
        if not test_id:
            return Response({"error": "test_id is required"}, status=400)

        try:
            test = newTest.objects.get(id=test_id)
        except newTest.DoesNotExist:
            return Response({"error": "Invalid test_id"}, status=404)

        saved = []

        for q in questions:
            obj = QuestionModel.objects.create(
                test=test,
                question=q.get("question", "").strip(),
                options=q.get("options", []),   # handles MCQ
                answer=q.get("answer", "").strip()
            )
            saved.append(obj.id)

        return Response({
            "status": "success",
            "saved_ids": saved
        })
        
class DeleteQuestionAPI(APIView):
    def post(self, request):
        q_id = request.data.get("id")
        QuestionModel.objects.filter(id=q_id).delete()
        return Response({"status": "deleted"})
        
class UpdateQuestionsAPI(APIView):
    def post(self, request):
        questions = request.data.get("questions", [])

        for q in questions:
            obj = QuestionModel.objects.get(id=q["id"])
            obj.question = q["question"]
            obj.options = q.get("options", [])
            obj.answer = q["answer"]
            obj.marks = q.get('marks', obj.marks)
            obj.save()

        return Response({"status": "updated"})

@login_required
def toggle_question(request):
    if request.method == "POST":
        data = json.loads(request.body)

        questions = data.get("questions", [])
        test_id = data.get("test_id")

        for q in questions:
            obj = QuestionModel.objects.get(id=q["question_id"], test_id=test_id)
            obj.is_selected = q["selected"]
            obj.marks = q["marks"]
            obj.save()

        return JsonResponse({"status": "success"})
        
@login_required
def delete_test(request, id):
    if request.method == "POST":
        newTest.objects.filter(id=id).delete()
        return JsonResponse({'status': 'ok'})
        
@login_required
def send_emails(request):
    data = json.loads(request.body)

    emails = data.get('emails', [])
    subject = data.get('subject')
    message = data.get('message')
    test_id = data.get('test_id')    
    datetime_str = data.get("datetime")
    if not emails or not test_id or not datetime_str:
        return JsonResponse({"status": "error", "message": "Missing data"})
        
    scheduled_time = parse_datetime(datetime_str)
    if timezone.is_naive(scheduled_time):
        scheduled_time = timezone.make_aware(scheduled_time)

    test = newTest.objects.get(id=test_id)

    email_tasks = []
    for email in emails:
        attempt = TestAttempt.objects.create(test=test, email=email, scheduled_at=scheduled_time)
        link = f"https://resume-screening-revamped.onrender.com/assessment-test/{attempt.token}/"
        final_message = message.replace(
            "[Will add automatically]",
            link
        )
        html_content = final_message.replace("\n", "<br>")
        email_tasks.append((email.strip(), subject, html_content))

    from resume_screening.background import run_in_background
    def send_all_emails():
        for email, subject, html_content in email_tasks:
            from resume_screening.email_service import send_brevo_email
            try:
                send_brevo_email(
                    to_email=email,
                    subject=subject,
                    html_content=html_content
                )
            except Exception as e:
                print(f"Failed to send email to {email}: {e}")

    run_in_background(send_all_emails)

    return JsonResponse({"status": "success"})
        
        
@login_required
def create_attempts(request):
    data = json.loads(request.body)

    test_id = data.get('test_id')
    emails = data.get('emails')

    test = newTest.objects.get(id=test_id)
    
    datetime_str = data.get("datetime")
    scheduled_time = parse_datetime(datetime_str)
    if timezone.is_naive(scheduled_time):
        scheduled_time = timezone.make_aware(scheduled_time)

    attempts = []

    for email in emails:
        attempt = TestAttempt.objects.create(test=test, email=email, scheduled_at=scheduled_time)

        link = f"https://resume-screening-revamped.onrender.com/assessment-test/{attempt.token}/"

        attempts.append({
            "email": email,
            "link": link
        })

    return JsonResponse({"attempts": attempts})
     
def submit_test(request):
    attempt_id = request.session.get('attempt_id')

    if attempt_id:
        attempt = TestAttempt.objects.get(id=attempt_id)
        attempt.status = 'submitted'
        attempt.save()

    # ✅ clear candidate session
    request.session.pop('is_candidate', None)
    request.session.pop('attempt_id', None)

    return HttpResponse("Test submitted")
    
@login_required
def result_api(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    answers = Answer.objects.filter(attempt=attempt).select_related('question')

    data = {
        "email": attempt.email,
        "score": attempt.score,
        "total_marks": sum(a.question.marks for a in answers),
        "answers": []
    }

    for a in answers:
        data["answers"].append({
            "question": a.question.question,
            "selected": a.selected_answer,
            "correct": a.question.answer,
            "marks": a.question.marks,
            "is_correct": a.selected_answer == a.question.answer
        })

    return JsonResponse(data)
    