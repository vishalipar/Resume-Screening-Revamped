from rest_framework.views import APIView
from rest_framework.response import Response
from .ai_assistant import AIAssistant
from .session_manager import get_or_create_state
from resume_parser.models import JobRole, Resume
import uuid

class ChatView(APIView):
    
    def post(self, request):
        user_message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id')
        
        if not user_message:
            return Response({'error': 'Message required'}, status=400)
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        state = get_or_create_state(session_id)
        assistant = AIAssistant()
        
        
        # Check for "list jobs" or "all jobs" request
        if state.stage == 'idle' and any(keyword in user_message.lower() for keyword in ['list jobs', 'all jobs', 'show jobs', 'available jobs']):
            
            jobs = JobRole.objects.filter(status='active')
            
            if not jobs.exists():
                return Response({
                    'session_id': session_id,
                    'message': "No job roles found. Create one to get started!",
                    'success': True
                })
            
            message = f"**Available Job Roles** (Total: {jobs.count()})\n\n"
            
            for i, job in enumerate(jobs, 1):
                message += f"**{i}. {job.title}**\n"
                message += f"   📍 {job.location or 'Not specified'} | "
                message += f"⏱️ {job.experience_required} years | "
                message += f"🔧 {len(job.required_skills)} skills required\n\n"
            
            message += "Type 'show job description for [job title]' to view full details."
            
            return Response({
                'session_id': session_id,
                'message': message,
                'jobs': [{
                    'id': job.id,
                    'title': job.title,
                    'location': job.location,
                    'experience_required': job.experience_required,
                    'skills_count': len(job.required_skills)
                } for job in jobs],
                'success': True
            })
            
        # Check for "show job" or "job description" request
        elif state.stage == 'idle' and any(keyword in user_message.lower() for keyword in ['show job', 'job description', 'job details', 'view job']):
            
            # Find the job mentioned
            jobs = JobRole.objects.filter(status='active')
            target_job = None
            
            for job in jobs:
                if job.title.lower() in user_message.lower():
                    target_job = job
                    break
            
            # If no job mentioned but only one exists, use it
            if not target_job and jobs.count() == 1:
                target_job = jobs.first()
            
            # If multiple jobs and none mentioned, ask
            if not target_job and jobs.count() > 1:
                state.stage = 'selecting_job_for_details'
                job_list = '\n'.join([f"- {job.title}" for job in jobs])
                return Response({
                    'session_id': session_id,
                    'message': f"Which job role?\n\n{job_list}\n\nPlease specify the job title.",
                    'success': True
                })
            
            # If no jobs exist
            if not target_job:
                return Response({
                    'session_id': session_id,
                    'message': "No job roles found. Please create a job role first.",
                    'success': True
                })
            
            # Build detailed JD display
            message = f"""
        📋 **Job Role: {target_job.title}**

        📝 **Description:**
        {target_job.description}

        🔧 **Required Skills:**
        {', '.join(target_job.required_skills)}

        ⏱️ **Experience Required:** {target_job.experience_required} years

        📍 **Location:** {target_job.location or 'Not specified'}

        💰 **Salary Range:** {target_job.salary_range or 'Not specified'}

📅 **Posted:** {target_job.created_at.strftime('%B %d, %Y')}

🟢 **Status:** {target_job.status.upper()}
    """
    
            return Response({
                'session_id': session_id,
                'message': message,
                'job_details': {
                    'id': target_job.id,
                    'title': target_job.title,
                    'description': target_job.description,
                    'required_skills': target_job.required_skills,
                    'experience_required': target_job.experience_required,
                    'location': target_job.location,
                    'salary_range': target_job.salary_range,
                    'created_at': target_job.created_at.isoformat(),
                    'status': target_job.status
                },
                'success': True
            })
            
        # Handle job selection for viewing details (NEW)
        elif state.stage == 'selecting_job_for_details':
            jobs = JobRole.objects.filter(status='active')
            target_job = None
            
            for job in jobs:
                if job.title.lower() in user_message.lower():
                    target_job = job
                    break
    
            if not target_job:
                return Response({
                    'session_id': session_id,
                    'message': "Job not found. Please enter a valid job title.",
                    'success': True
                })
            
            state.stage = 'idle'  # Reset state
            
            message = f"""
            📋 **Job Role: {target_job.title}**

            📝 **Description:**
            {target_job.description}

            🔧 **Required Skills:**
            {', '.join(target_job.required_skills)}

            ⏱️ **Experience Required:** {target_job.experience_required} years

            📍 **Location:** {target_job.location or 'Not specified'}

            💰 **Salary Range:** {target_job.salary_range or 'Not specified'}

            📅 **Posted:** {target_job.created_at.strftime('%B %d, %Y')}

            🟢 **Status:** {target_job.status.upper()}
                """
                
            return Response({
                'session_id': session_id,
                'message': message,
                'job_details': {
                    'id': target_job.id,
                    'title': target_job.title,
                    'description': target_job.description,
                    'required_skills': target_job.required_skills,
                    'experience_required': target_job.experience_required,
                    'location': target_job.location,
                    'salary_range': target_job.salary_range,
                    'created_at': target_job.created_at.isoformat(),
                    'status': target_job.status
                },
                'success': True
            })
        
        # Check for matching request - IMPROVED
        elif state.stage == 'idle' and any(keyword in user_message.lower() for keyword in ['match', 'score', 'calculate']):
            
            # Find the job mentioned in message
            jobs = JobRole.objects.filter(status='active')
            target_job = None
            
            # Try to find job by title in message
            for job in jobs:
                if job.title.lower() in user_message.lower():
                    target_job = job
                    break
            
            # If no job mentioned but only one exists, use it
            if not target_job and jobs.count() == 1:
                target_job = jobs.first()
            
            # If multiple jobs and none mentioned, list them
            if not target_job and jobs.count() > 1:
                state.stage = 'selecting_job_for_matching'
                job_list = '\n'.join([f"- {job.title}" for job in jobs])
                return Response({
                    'session_id': session_id,
                    'message': f"Which job role do you want to match against?\n\n{job_list}\n\nPlease specify the job title.",
                    'success': True
                })
            
            # If no jobs exist
            if not target_job:
                return Response({
                    'session_id': session_id,
                    'message': "No job roles found in database. Please create a job role first.",
                    'success': True
                })
            
            # Check if resume exists
            if not Resume.objects.exists():
                return Response({
                    'session_id': session_id,
                    'message': "No resumes uploaded yet. Please upload a resume first.",
                    'success': True
                })
            
            recent_resume = Resume.objects.last()
            
            # Calculate match
            match_score = assistant.calculate_match_score(recent_resume, target_job)
            
            message = f"""
        **Match Analysis for {recent_resume.name}:**

        **Job Role:** {target_job.title}
        **Match Score:** {match_score}%

        **Candidate Skills:** {', '.join(recent_resume.skills) if recent_resume.skills else 'None found'}
        **Required Skills:** {', '.join(target_job.required_skills)}

        **Candidate Experience:** {recent_resume.experience_years} years
        **Required Experience:** {target_job.experience_required} years

        {'✅ **Strong Match!**' if match_score >= 70 else '⚠️ **Partial Match**' if match_score >= 50 else '❌ **Weak Match**'}
            """
            
            return Response({
                'session_id': session_id,
                'message': message,
                'match_score': match_score,
                'success': True
            })
            
        # Handle job selection for matching (NEW)
        elif state.stage == 'selecting_job_for_matching':
            jobs = JobRole.objects.filter(status='active')
            target_job = None
            
            for job in jobs:
                if job.title.lower() in user_message.lower():
                    target_job = job
                    break
            
            if not target_job:
                return Response({
                    'session_id': session_id,
                    'message': "Job not found. Please enter a valid job title.",
                    'success': True
                })
            
            state.stage = 'idle'  # Reset state
    
            if not Resume.objects.exists():
                return Response({
                    'session_id': session_id,
                    'message': "No resumes uploaded yet.",
                    'success': True
                })
            
            recent_resume = Resume.objects.last()
            match_score = assistant.calculate_match_score(recent_resume, target_job)
            
            message = f"""
        **Match Analysis for {recent_resume.name}:**

        **Job Role:** {target_job.title}
        **Match Score:** {match_score}%

        **Candidate Skills:** {', '.join(recent_resume.skills) if recent_resume.skills else 'None found'}
        **Required Skills:** {', '.join(target_job.required_skills)}

        **Candidate Experience:** {recent_resume.experience_years} years
        **Required Experience:** {target_job.experience_required} years

        {'✅ **Strong Match!**' if match_score >= 70 else '⚠️ **Partial Match**' if match_score >= 50 else '❌ **Weak Match**'}
        """
    
            return Response({
                'session_id': session_id,
                'message': message,
                'match_score': match_score,
                'success': True
            })
            
        # Check for job creation intent
        elif state.stage == 'idle' and any(keyword in user_message.lower() for keyword in ['create job', 'new job', 'add job']):
            state.stage = 'collecting_jd'
            return Response({
                'session_id': session_id,
                'message': "Great! Let's create a new job role. What is the job title?",
                'success': True
            })
            
        # Collecting JD information
        elif state.stage == 'collecting_jd':
            
            # Job Title
            if 'title' not in state.jd_data:
                state.jd_data['title'] = user_message
                return Response({
                    'session_id': session_id,
                    'message': "What is the job description? (You can say 'generate for me' and I'll create one)",
                    'success': True
                })
            
            # Job Description - AUTO GENERATE if requested
            elif 'description' not in state.jd_data:
                # Check if user wants AI to generate
                if any(keyword in user_message.lower() for keyword in ['generate', 'create', 'write', 'make', 'whatever', 'you decide', 'suggest']):
                    # Generate description using AI
                    generated = self._generate_jd_content(
                        state.jd_data['title'], 
                        'description'
                    )
                    state.jd_data['description'] = generated
                    
                    return Response({
                        'session_id': session_id,
                        'message': f"I've generated this description:\n\n{generated}\n\nWhat skills are required? (Say 'generate' for auto-suggestion)",
                        'success': True
                    })
                else:
                    state.jd_data['description'] = user_message
                    return Response({
                        'session_id': session_id,
                        'message': "What skills are required? (comma separated, or say 'generate for me')",
                        'success': True
                    })
            
            # Required Skills - AUTO GENERATE if requested
            elif 'required_skills' not in state.jd_data:
                if any(keyword in user_message.lower() for keyword in ['generate', 'create', 'write', 'whatever', 'suggest', 'you decide']):
                    # Generate skills using AI
                    generated_skills = self._generate_jd_content(
                        state.jd_data['title'], 
                        'skills'
                    )
                    state.jd_data['required_skills'] = [s.strip() for s in generated_skills.split(',')]
                    
                    return Response({
                        'session_id': session_id,
                        'message': f"I've suggested these skills:\n\n{generated_skills}\n\nHow many years of experience required? (type a number or 0 for freshers)",
                        'success': True
                    })
                else:
                    state.jd_data['required_skills'] = [s.strip() for s in user_message.split(',')]
                    return Response({
                        'session_id': session_id,
                        'message': "How many years of experience required? (type a number or 0 for freshers)",
                        'success': True
                    })
            
            # Experience
            elif 'experience_required' not in state.jd_data:
                try:
                    exp = int(''.join(filter(str.isdigit, user_message)))
                    state.jd_data['experience_required'] = exp
                except:
                    state.jd_data['experience_required'] = 0
                
                return Response({
                    'session_id': session_id,
                    'message': "What is the job location? (type location or 'remote' or 'skip')",
                    'success': True
                })
            
            # Location
            elif 'location' not in state.jd_data:
                if user_message.lower() != 'skip':
                    state.jd_data['location'] = user_message
                else:
                    state.jd_data['location'] = ''
                
                # Move to confirmation
                state.stage = 'confirming_jd'
                
                summary = f"""
Here's the job role summary:

📋 **Title:** {state.jd_data.get('title')}

📝 **Description:** 
{state.jd_data.get('description')}

🔧 **Required Skills:** {', '.join(state.jd_data.get('required_skills', []))}

⏱️ **Experience:** {state.jd_data.get('experience_required')} years

📍 **Location:** {state.jd_data.get('location') or 'Not specified'}

---
Do you want to save this job role? 
Reply 'yes' to confirm, 'no' to cancel, or 'edit [field]' to make changes.
                """
                
                return Response({
                    'session_id': session_id,
                    'message': summary,
                    'success': True
                })
        
        # Confirming JD
        elif state.stage == 'confirming_jd':
            if user_message.lower() in ['yes', 'confirm', 'save', 'ok']:
                job = JobRole.objects.create(
                    title=state.jd_data.get('title'),
                    description=state.jd_data.get('description'),
                    required_skills=state.jd_data.get('required_skills', []),
                    experience_required=state.jd_data.get('experience_required', 0),
                    location=state.jd_data.get('location', '')
                )
                
                state.reset()
                
                return Response({
                    'session_id': session_id,
                    'message': f"✅ Job role '{job.title}' has been saved successfully! You can now upload resumes to match against this role.",
                    'job_created': True,
                    'job_id': job.id,
                    'success': True
                })
            
            elif user_message.lower() in ['no', 'cancel']:
                state.reset()
                return Response({
                    'session_id': session_id,
                    'message': "Job creation cancelled. How else can I help you?",
                    'success': True
                })
            
            # Handle ADD operations
            elif 'add' in user_message.lower() and 'skill' in user_message.lower():
                # Extract skill to add
                import re
                # Pattern: "add [skill] to skills"
                match = re.search(r'add\s+(.+?)\s+to\s+skill', user_message.lower())
                if match:
                    new_skill = match.group(1).strip()
                    state.jd_data['required_skills'].append(new_skill)
                    
                    summary = f"""
        Updated! Here's the new summary:

        📋 **Title:** {state.jd_data.get('title')}

        📝 **Description:** 
        {state.jd_data.get('description')}

        🔧 **Required Skills:** {', '.join(state.jd_data.get('required_skills', []))}

        ⏱️ **Experience:** {state.jd_data.get('experience_required')} years

        📍 **Location:** {state.jd_data.get('location') or 'Not specified'}

        ---
        Reply 'yes' to save, 'no' to cancel, or make more edits.
                    """
                    
                    return Response({
                        'session_id': session_id,
                        'message': summary,
                        'success': True
                    })
                else:
                    return Response({
                        'session_id': session_id,
                        'message': "Please specify like: 'add Machine Learning to skills'",
                        'success': True
                    })
            
            # Handle REMOVE operations
            elif 'remove' in user_message.lower() and 'skill' in user_message.lower():
                import re
                match = re.search(r'remove\s+(.+?)\s+from\s+skill', user_message.lower())
                if match:
                    skill_to_remove = match.group(1).strip()
                    current_skills = state.jd_data.get('required_skills', [])
                    # Case-insensitive removal
                    updated_skills = [s for s in current_skills if s.lower() != skill_to_remove.lower()]
                    
                    if len(updated_skills) == len(current_skills):
                        return Response({
                            'session_id': session_id,
                            'message': f"Skill '{skill_to_remove}' not found. Current skills: {', '.join(current_skills)}",
                            'success': True
                        })
                    
                    state.jd_data['required_skills'] = updated_skills
                    
                    summary = f"""
        Updated! Here's the new summary:

        📋 **Title:** {state.jd_data.get('title')}

        📝 **Description:** 
        {state.jd_data.get('description')}

        🔧 **Required Skills:** {', '.join(state.jd_data.get('required_skills', []))}

        ⏱️ **Experience:** {state.jd_data.get('experience_required')} years

        📍 **Location:** {state.jd_data.get('location') or 'Not specified'}

        ---
        Reply 'yes' to save, 'no' to cancel, or make more edits.
                    """
                    
                    return Response({
                        'session_id': session_id,
                        'message': summary,
                        'success': True
                    })
    
            # Handle EDIT operations (replace entire field)
            elif user_message.lower().startswith('edit'):
                # Detect which field
                field_name = None
                if 'title' in user_message.lower():
                    field_name = 'title'
                elif 'description' in user_message.lower():
                    field_name = 'description'
                elif 'skill' in user_message.lower():
                    field_name = 'skills'
                elif 'experience' in user_message.lower():
                    field_name = 'experience'
                elif 'location' in user_message.lower():
                    field_name = 'location'
                
                if field_name:
                    state.stage = f'editing_{field_name}'
                    state.jd_data['editing_field'] = field_name
                    
                    return Response({
                        'session_id': session_id,
                        'message': f"What's the new value for **{field_name}**?",
                        'success': True
                    })
                else:
                    return Response({
                        'session_id': session_id,
                        'message': "Which field? (title, description, skills, experience, location)",
                        'success': True
                    })
            
            else:
                return Response({
                    'session_id': session_id,
                    'message': "Please reply:\n- 'yes' to save\n- 'no' to cancel\n- 'edit [field]' to change a field\n- 'add [skill] to skills' to add a skill\n- 'remove [skill] from skills' to remove a skill",
                    'success': True
                })

        # Handle editing process (NEW SECTION - Add before "Check for job creation intent")
        elif state.stage.startswith('editing_'):
            field_name = state.jd_data.get('editing_field')
            
            if field_name == 'title':
                state.jd_data['title'] = user_message
            elif field_name == 'description':
                state.jd_data['description'] = user_message
            elif field_name == 'skills':
                state.jd_data['required_skills'] = [s.strip() for s in user_message.split(',')]
            elif field_name == 'experience':
                try:
                    exp = int(''.join(filter(str.isdigit, user_message)))
                    state.jd_data['experience_required'] = exp
                except:
                    state.jd_data['experience_required'] = 0
            elif field_name == 'location':
                state.jd_data['location'] = user_message
            
            # Go back to confirmation
            state.stage = 'confirming_jd'
            
            summary = f"""
        Updated! Here's the new summary:

        📋 **Title:** {state.jd_data.get('title')}

        📝 **Description:** 
        {state.jd_data.get('description')}

        🔧 **Required Skills:** {', '.join(state.jd_data.get('required_skills', []))}

        ⏱️ **Experience:** {state.jd_data.get('experience_required')} years

        📍 **Location:** {state.jd_data.get('location') or 'Not specified'}

        ---
        Reply 'yes' to save, 'no' to cancel, or make more edits.
            """
            
            return Response({
                'session_id': session_id,
                'message': summary,
                'success': True
            })
    
        # Normal chat
        else:
            result = assistant.chat(user_message)
            
            return Response({
                'session_id': session_id,
                'message': result['message'],
                'success': result['success']
            })
    
    def _generate_jd_content(self, job_title, content_type):
        """Use AI to generate JD content"""
        assistant = AIAssistant()
        
        if content_type == 'description':
            prompt = f"""Write a professional job description for '{job_title}' role suitable for freshers. 
Include responsibilities and what the candidate will learn. Keep it concise (3-4 sentences).
Only return the description, nothing else."""
            
        elif content_type == 'skills':
            prompt = f"""List the essential technical skills required for a '{job_title}' position for freshers.
Return ONLY comma-separated skills (e.g., Python, Django, SQL). Maximum 6 skills.
Only return the skills list, nothing else."""
        
        result = assistant.chat(prompt)
        return result['message'].strip()