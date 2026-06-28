from groq import Groq
from django.conf import settings
from resume_parser.models import JobRole
import re
import json

client = Groq(api_key=settings.GROQ_API_KEY)

class AIAssistant:
    def chat(self, user_message):
        active_jobs = JobRole.objects.filter(status='active')
        
        context = ""
        
        if active_jobs.exists():
            context += f"\nActive jobs: {', '.join([j.title for j in active_jobs])}"
        
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Free model
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an HR assistant helping to find candidates. Be helpful and concise. Dont give answers if the questions are not related to the hr work or resume work, just say to ask to related questions.
Current Context:{context}

When user wants to create a job, ask step by step:
1. Job title?
2. Job description?
3. Required skills (comma separated)?
4. Years of experience required?
5. Location?

When user asks about resume, reference the uploaded resume details.
When user asks to match resume to a job, calculate match score based on skills overlap."""
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                max_tokens=400
            )

            return {
                'message': response.choices[0].message.content,
                'success': True
            }

        except Exception as e:
            return {
                'message': f"Error: {str(e)}",
                'success': False
            }
            
    def extract_jb_info(self, text):
        jd_data = {}
        
        # Extract title 
        title_match = re.search(r'(?:title|role|position)[:\s]+([^\n,]+)', text, re.IGNORECASE)
        if title_match:
            jd_data['title'] = title_match.group(1).strip()
            
        # Extract skills
        skills_match = re.search(r'(?:skills?|technologies?)[:\s]+([^\n]+)', text,re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(1)
            jd_data['required_skills'] = [s.strip() for s in skills_text.split(',')]
            
        # Extract experience
        exp_match = re.search(fr'(\d+)\+?\s*(?:years?|yrs)', text, re.IGNORECASE)
        if exp_match:
            jd_data['experience_required'] = int(exp_match.group(1))
            
        # Extract location
        location_match = re.search(r'(?:location|based in)[:\s]+([^\n,]+)', text, re.IGNORECASE)
        if location_match:
            jd_data['location'] = location_match.group(1).strip()
            
        return jd_data
        
    def calculate_match_score(self, resume, job):
        """Calculate match score between resume and job"""
        resume_skills = set([s.lower() for s in resume.skills])
        job_skills = set([s.lower() for s in job.required_skills])
        
        if not job_skills:
            return 0
        
        matching_skills = resume_skills.intersection(job_skills)
        skill_match = (len(matching_skills) / len(job_skills)) * 100
        
        # Experience match
        if resume.experience_years >= job.experience_required:
            exp_match = 100
        else:
            exp_match = (resume.experience_years / job.experience_required) * 100
        
        # Weighted average (60% skills, 40% experience)
        final_score = (skill_match * 0.6) + (exp_match * 0.4)
        
        return round(final_score, 1)