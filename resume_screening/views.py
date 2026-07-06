from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
import pdfplumber
import docx
import re
from sklearn.metrics.pairwise import cosine_similarity
from .models import UserInfo
from resume_parser.models import JobRole
from django.core.mail import send_mail, send_mass_mail
from django.contrib import messages
from resume_project.settings import EMAIL_HOST_USER
from openpyxl import Workbook
from django.http import HttpResponse
from datetime import datetime
from django.db.models import Avg


nlp = None
model = None

def load_models():
    global nlp, model
    import spacy
    if nlp is None:
        nlp = spacy.load("en_core_web_sm")
    
    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])
    
def extract_job_title_from_jd(jd_text):
    """Enhanced job title extraction"""
    
    # Pattern 1: Look for "Job Title:" label
    title_pattern = r'(?:job\s+title|position|role)[\s:]+([^\n]+)'
    match = re.search(title_pattern, jd_text, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Clean up common suffixes
        title = re.sub(r'\s*[-:]\s*$', '', title)
        return title[:100]
    
    # Pattern 2: First line if it looks like a title (capitalized, reasonable length)
    lines = [line.strip() for line in jd_text.split('\n') if line.strip()]
    if lines:
        first_line = lines[0]
        # Check if it's not too long and doesn't contain common description words
        if 5 <= len(first_line) <= 100 and not any(word in first_line.lower() for word in ['description', 'summary', 'overview', 'reports to']):
            return first_line
    
    return "Untitled Position"
    
def extract_skills_from_jd(jd_text):
    """Enhanced skill extraction with multiple methods"""
    
    # Expanded skills database with variations
    skills_database = {
        # Software & Tools
        'microsoft word': ['word', 'ms word', 'microsoft word'],
        'microsoft excel': ['excel', 'ms excel', 'microsoft excel', 'spreadsheet'],
        'microsoft office': ['ms office', 'microsoft office', 'office suite'],
        'powerpoint': ['powerpoint', 'ppt', 'presentations'],
        
        # HR Specific
        'hris': ['hris', 'hr information system', 'human resources information system', 'hris management'],
        'applicant tracking': ['ats', 'applicant tracking', 'applicant tracking system'],
        'payroll': ['payroll', 'payroll processing', 'payroll management'],
        'benefits administration': ['benefits', 'benefits administration', 'employee benefits'],
        'recruitment': ['recruitment', 'recruiting', 'talent acquisition'],
        'employee relations': ['employee relations', 'employee engagement'],
        'performance management': ['performance management', 'performance review'],
        'compliance': ['compliance', 'hr compliance', 'regulatory compliance'],
        'employment law': ['employment law', 'labor law', 'hr law'],
        
        # Technical
        'python': ['python'],
        'java': ['java'],
        'javascript': ['javascript', 'js'],
        'sql': ['sql', 'database', 'mysql', 'postgresql'],
        'html': ['html', 'html5'],
        'css': ['css', 'css3', 'styling'],
        'react': ['react', 'reactjs', 'react.js'],
        'django': ['django'],
        'node': ['node', 'nodejs', 'node.js'],
        'aws': ['aws', 'amazon web services', 'cloud'],
        'docker': ['docker', 'containerization'],
        'git': ['git', 'github', 'version control'],
        
        # Soft Skills
        'communication': ['communication', 'oral communication', 'written communication'],
        'leadership': ['leadership', 'team leadership'],
        'problem solving': ['problem solving', 'analytical'],
        'time management': ['time management', 'organization'],
        'teamwork': ['teamwork', 'collaboration', 'team player'],
        'confidentiality': ['confidentiality', 'confidential'],
    }
    
    found_skills = []
    jd_lower = jd_text.lower()
    
    # Check each skill and its variations
    for skill_name, variations in skills_database.items():
        for variation in variations:
            if variation in jd_lower:
                # Capitalize properly
                display_name = skill_name.title() if skill_name.islower() else skill_name.upper()
                if display_name not in found_skills:
                    found_skills.append(display_name)
                break
    
    # If no skills found, look for qualification/requirement sections
    if not found_skills:
        # Extract from qualifications section
        qual_pattern = r'(?:qualifications?|requirements?|skills?)[\s:]+([^\n]+(?:\n[^\n]+){0,10})'
        qual_match = re.search(qual_pattern, jd_text, re.IGNORECASE)
        if qual_match:
            qual_text = qual_match.group(1)
            # Simple word extraction from qualifications
            common_skills = ['excel', 'word', 'communication', 'management', 'sql', 'python']
            for skill in common_skills:
                if skill in qual_text.lower() and skill.title() not in found_skills:
                    found_skills.append(skill.title())
    
    return found_skills if found_skills else ['General']

def extract_experience_from_jd(jd_text):
    """Enhanced experience extraction"""
    
    # Pattern 1: Direct years mention
    patterns = [
        r'(\d+)[\+]?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)',
        r'(?:experience|exp)(?:\s+of)?\s+(\d+)[\+]?\s*(?:years?|yrs?)',
        r'minimum\s+(?:of\s+)?(\d+)[\+]?\s*(?:years?|yrs?)',
        r'at\s+least\s+(\d+)[\+]?\s*(?:years?|yrs?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                continue
    
    # Check for entry-level, junior, senior keywords
    jd_lower = jd_text.lower()
    if any(word in jd_lower for word in ['entry level', 'entry-level', 'fresher', 'graduate', 'intern']):
        return 0
    elif any(word in jd_lower for word in ['junior', '1-2 years', '1 to 2']):
        return 1
    elif any(word in jd_lower for word in ['mid-level', 'intermediate', '3-5 years']):
        return 3
    elif any(word in jd_lower for word in ['senior', 'lead', '5+ years', '5-7 years']):
        return 5
    
    return 0  # Default for no experience mentioned


def extract_location_from_jd(jd_text):
    """Enhanced location extraction"""
    
    # Pattern 1: Explicit location label
    location_patterns = [
        r'(?:location|office|based\s+(?:in|at)|work\s+location)[\s:]+([^\n]+)',
        r'(?:city|state|country)[\s:]+([^\n]+)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up
            location = re.sub(r'[,;].*$', '', location)  # Take only first part before comma
            return location[:100]
    
    # Check for common location keywords
    jd_lower = jd_text.lower()
    if 'remote' in jd_lower or 'work from home' in jd_lower:
        return 'Remote'
    
    # Look for city names (common US cities as example)
    common_cities = ['new york', 'san francisco', 'chicago', 'boston', 'austin', 
                     'seattle', 'los angeles', 'miami', 'denver', 'atlanta']
    for city in common_cities:
        if city in jd_lower:
            return city.title()
    
    return ''


def extract_jd_details(jd_text):
    """Main function to extract all JD details"""
    
    # Extract title
    title = extract_job_title_from_jd(jd_text)
    
    # Extract skills
    skills = extract_skills_from_jd(jd_text)
    
    # Extract experience
    experience = extract_experience_from_jd(jd_text)
    
    # Extract location
    location = extract_location_from_jd(jd_text)
    
    # Use full text as description (or first 1000 chars)
    description = jd_text[:1000] if len(jd_text) > 1000 else jd_text
    
    return {
        'title': title,
        'description': description,
        'required_skills': skills,
        'experience_required': experience,
        'location': location
    }
    
def extract_text(file):
    if file.name.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif file.name.endswith(".docx"):
        return extract_text_from_docx(file)
    else:
        return file.read().decode("utf-8")

def match_score(jd_text, resume_text):
    load_models()
    jd_vec = model.encode(jd_text)
    res_vec = model.encode(resume_text)
    return float(cosine_similarity([jd_vec], [res_vec])[0][0]) * 100

def extract_resume_details(resume_text):
    load_models()
    doc = nlp(resume_text)
    
    # Extract email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text)
    email = email_match.group(0) if email_match else "Not found"
    
    # name = email.split('@')[0]
    name = re.sub(r'[^a-zA-Z\s]', '', email.split('@')[0]).capitalize()
    
    # Extract skills (predefined list matching)
    skills_list = [
        'Python', 'Django', 'JavaScript', 'React', 'Node.js', 'Java', 'C++', 
        'SQL', 'PostgreSQL', 'MongoDB', 'AWS', 'Docker', 'Kubernetes', 
        'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch',
        'Git', 'HTML', 'CSS', 'REST API', 'Flask', 'FastAPI', 'HR Software Proficiency', 'Email Management', 'HRIS Management', 'Data Management'
    ]
    
    # Find skills present in resume
    resume_lower = resume_text.lower()
    found_skills = [skill for skill in skills_list if skill.lower() in resume_lower]
    
    return {
        'name': name,
        'email': email,
        'skills': found_skills[:5]  # Top 5 skills
    }
    
@login_required
def home(request):
    job_roles = JobRole.objects.filter(status='active').order_by('-created_at')
    
    context = {
        'jd_text': None, 
        'results': [],
        'job_roles': job_roles,
        'selected_job_title': None,
        'selected_job_id': None
    }
    
    if request.method == 'POST':
        jd_mode = request.POST.get('jd_mode')
        
        # Handle JD upload from file
        if jd_mode == 'upload' and 'jd_file' in request.FILES:
            jd_file = request.FILES['jd_file']
            jd_text = extract_text(jd_file)
            
            # Extract JD details using improved function
            jd_details = extract_jd_details(jd_text)
            
            # CHECK FOR DUPLICATE JD BY TITLE
            existing_job = JobRole.objects.filter(
                title__iexact=jd_details['title'],  # Case-insensitive match
                status='active'
            ).first()
            
            if existing_job:
                # Use existing JobRole instead of creating new one
                request.session['jd_text'] = jd_text
                request.session['selected_job_id'] = existing_job.id
                request.session['selected_job_title'] = existing_job.title
                
                context['jd_text'] = jd_text[:300] + "..." if len(jd_text) > 300 else jd_text
                context['selected_job_title'] = existing_job.title
                context['selected_job_id'] = existing_job.id
                context['jd_already_exists'] = True  # NEW FLAG
            else:
                # Store extracted details in session for confirmation
                request.session['jd_text'] = jd_text
                request.session['pending_jd'] = {
                    'title': jd_details['title'],
                    'description': jd_details['description'],
                    'required_skills': jd_details['required_skills'],
                    'experience_required': jd_details['experience_required'],
                    'location': jd_details['location']
                }
                
                # Show confirmation screen
                context['show_jd_confirmation'] = True
                context['jd_details'] = jd_details
                context['jd_text'] = jd_text[:300] + "..." if len(jd_text) > 300 else jd_text
        # Handle JD confirmation after review
        elif 'confirm_jd' in request.POST and 'pending_jd' in request.session:
            pending_jd = request.session['pending_jd']
            
            # Get manually added/edited skills
            updated_title = request.POST.get('jd_title', pending_jd['title'])
            updated_skills = request.POST.get('jd_skills', '')
            updated_experience = request.POST.get('jd_experience', pending_jd['experience_required'])
            updated_location = request.POST.get('jd_location', pending_jd['location'])
            
            # Parse skills (comma-separated)
            if updated_skills:
                skills_list = [s.strip() for s in updated_skills.split(',') if s.strip()]
            else:
                skills_list = pending_jd['required_skills']
            
            # Create JobRole
            job_role = JobRole.objects.create(
                title=updated_title,
                description=pending_jd['description'],
                required_skills=skills_list,
                experience_required=int(updated_experience),
                location=updated_location,
                status='active'
            )
            
            # Store in session
            request.session['selected_job_id'] = job_role.id
            request.session['selected_job_title'] = job_role.title
            
            # Clear pending JD
            del request.session['pending_jd']
            
            context['jd_text'] = request.session['jd_text'][:300] + "..."
            context['selected_job_title'] = job_role.title
            context['selected_job_id'] = job_role.id
            context['jd_saved'] = True

        # Handle cancel JD confirmation
        elif 'cancel_jd' in request.POST:
            if 'pending_jd' in request.session:
                del request.session['pending_jd']
            if 'jd_text' in request.session:
                del request.session['jd_text']
            context['jd_cancelled'] = True 
              
        # Handle JD selection from saved job roles
        elif jd_mode == 'select' and 'job_role_id' in request.POST:
            job_id = request.POST.get('job_role_id')
            try:
                job = JobRole.objects.get(id=job_id)
                jd_text = f"{job.title}\n\n{job.description}\n\nRequired Skills: {', '.join(job.required_skills)}\nExperience: {job.experience_required} years\nLocation: {job.location or 'Not specified'}"
                
                request.session['jd_text'] = jd_text
                request.session['selected_job_id'] = job.id
                request.session['selected_job_title'] = job.title
                
                context['jd_text'] = jd_text[:300] + "..." if len(jd_text) > 300 else jd_text
                context['selected_job_title'] = job.title
                context['selected_job_id'] = job.id
            except JobRole.DoesNotExist:
                context['error'] = 'Selected job role not found'
        
        # Handle resume screening
        elif 'resume_files' in request.FILES and 'jd_text' in request.session:
            jd_text = request.session['jd_text']
            resume_files = request.FILES.getlist('resume_files')
            selected_job_id = request.session.get('selected_job_id')
            
            results = []
            for resume_file in resume_files:
                resume_text = extract_text(resume_file)
                details = extract_resume_details(resume_text)
                score = match_score(jd_text, resume_text)
                
                status = True if score >= 80 else False
                
                # Create UserInfo and link to job role
                user_info = UserInfo.objects.create(
                    name=details['name'],
                    email=details['email'],
                    skills=details['skills'],
                    score=score,
                    resume=resume_file,
                    status=status,
                    job_role_id=selected_job_id  # LINK TO JOB ROLE
                )
                
                results.append({
                    'name': resume_file.name,
                    'score': f"{score:.2f}"
                })
            
            context['results'] = results
            context['jd_text'] = jd_text[:300] + "..." if len(jd_text) > 300 else jd_text
            context['selected_job_title'] = request.session.get('selected_job_title')
            context['selected_job_id'] = selected_job_id
    
    # Load session data if exists
    elif 'jd_text' in request.session:
        jd_text = request.session['jd_text']
        context['jd_text'] = jd_text[:300] + "..." if len(jd_text) > 300 else jd_text
        context['selected_job_title'] = request.session.get('selected_job_title')
        context['selected_job_id'] = request.session.get('selected_job_id')
    
    return render(request, 'home.html', context)  
    
@login_required
def candidates(request):
    # Get filter parameter
    job_filter = request.GET.get('job_role', 'all')
    
    # Filter users based on selection
    if job_filter == 'all':
        users = UserInfo.objects.all()
    else:
        users = UserInfo.objects.filter(job_role_id=job_filter)
    
    # Get all job roles for dropdown
    job_roles = JobRole.objects.filter(userinfo__isnull=False).distinct().order_by('-created_at')
    
    candidates = users.count()
    
    context = {
        'candidates': candidates,
        'users': users,
        'job_roles': job_roles,
        'selected_job': job_filter,
    }
    return render(request, 'candidates.html', context)
    
@login_required
def delete_user(request, user_id):
    UserInfo.objects.filter(id = user_id).delete()
    return redirect('candidates')
    
@login_required
def send_email_view(request):
    if request.method == 'POST':
        to_email = request.POST.get('to_email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        from .background import run_in_background
        try:
            # run_in_background(
            #     send_mail,
            #     subject,
            #     message,
            #     "sampleemail811@gmail.com",
            #     [to_email],
            #     fail_silently=False
            # )
            
            from resume_screening.email_service import send_brevo_email
            # run_in_background(
            #     send_brevo_email,
            #     [to_email],
            #     subject,
            #     html_content
            # )

            send_brevo_email(
                to_email=to_email,
                subject=subject,
                html_content=message
            )
            messages.success(request, 'Email is being sent in the background.')
        except Exception as e:
            messages.error(request, 'Failed to queue email.')
            
        return redirect('candidates')
        
@login_required
def export_candidates(request):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Candidates'
    
    headers = ['Name','Email','Role','Match Score', 'Skills', 'Status']
    ws.append(headers)
    
    candidates = UserInfo.objects.all()
    for candidate in candidates:
        skills = ', '.join(candidate.skills) if isinstance(candidate.skills, list) else candidate.skills
        status = 'Shortlisted' if candidate.status else 'Review'
        role_title = candidate.job_role.title if candidate.job_role else 'Not Assigned'
        ws.append([
            candidate.name,
            candidate.email,
            role_title,
            f"{candidate.score}%",
            skills,
            status
        ])
        
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=candidates.xlsx'
    
    wb.save(response)
    return response

@login_required
def schedule_interviews(request):
    if request.method == 'POST':
        candidate_ids = request.POST.getlist('candidates')
        interview_datetime = request.POST.get('interview_datetime')
        subject = request.POST.get('subject')
        message_template = request.POST.get('message')
        
        # Format datetime
        dt = datetime.strptime(interview_datetime, '%Y-%m-%dT%H:%M')
        formatted_datetime = dt.strftime('%B %d, %Y at %I:%M %p')
        
        # Replace placeholder in message
        message = message_template.replace('[Will be filled automatically]', formatted_datetime)
        
        # Get candidates
        candidates = UserInfo.objects.filter(id__in=candidate_ids)
        
        # Prepare emails
        emails = []
        for candidate in candidates:
            personalized_message = message.replace('Dear Candidate', f'Dear {candidate.name}')
            emails.append((
                subject,
                personalized_message,
                EMAIL_HOST_USER,  # From email
                [candidate.email]
            ))
        
        # Send emails
        from .background import run_in_background
        try:
            run_in_background(send_mass_mail, emails, fail_silently=False)
            messages.success(request, f'Interview invitations are being sent in the background to {len(emails)} candidates!')
        except Exception as e:
            messages.error(request, f'Failed to queue emails: {str(e)}')
        
        return redirect('candidates')
        
@login_required
def dashboard(request):
    candidates = UserInfo.objects.all().order_by('-score')
    top_candidates = candidates[:5]
    
    total_candidates = len(candidates)
    shortlisted = 0
    review = 0
    for candidate in candidates:
        if candidate.status == True:
            shortlisted += 1
        else:
            review += 1
    avg_score = UserInfo.objects.aggregate(Avg('score'))['score__avg'] or 0
    
    context = {
        'candidates':candidates,
        'top_candidates':top_candidates,
        'total_candidates':total_candidates,
        'shortlisted':shortlisted,
        'review':review,
        'avg_score':avg_score,
    }
    return render(request, 'dashboard.html', context)