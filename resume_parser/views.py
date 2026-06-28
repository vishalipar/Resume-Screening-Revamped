from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from .models import JobRole, Resume
from django.shortcuts import render


class JobRoleView(APIView):
    """Create and list job roles"""
    
    def get(self, request):
        """List all active job roles"""
        jobs = JobRole.objects.filter(status='active')
        data = [{
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'required_skills': job.required_skills,
            'experience_required': job.experience_required,
            'location': job.location
        } for job in jobs]
        
        return Response({'jobs': data})
    
    def post(self, request):
        """Create new job role"""
        data = request.data
        
        job = JobRole.objects.create(
            title=data.get('title'),
            description=data.get('description'),
            required_skills=data.get('required_skills', []),
            experience_required=data.get('experience_required', 0),
            education_level=data.get('education_level', ''),
            location=data.get('location', ''),
            salary_range=data.get('salary_range', '')
        )
        
        return Response({
            'message': 'Job role created successfully',
            'id': job.id,
            'title': job.title
        })
        
def job_roles_view(request):
    return render(request, 'job_roles.html')
    
class JobRolesAPIView(APIView):
    """API to get all job roles"""
    
    def get(self, request):
        jobs = JobRole.objects.all().order_by('-created_at')
        
        data = []
        for job in jobs:
            data.append({
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'required_skills': job.required_skills,
                'experience_required': job.experience_required,
                'location': job.location,
                'salary_range': job.salary_range,
                'status': job.status,
                'created_at': job.created_at.strftime('%B %d, %Y')
            })
        
        return Response({'jobs': data})
        
    def put(self, request, job_id):
        """Update a job role"""
        try:
            job = JobRole.objects.get(id=job_id)
            
            # Update fields
            job.title = request.data.get('title', job.title)
            job.description = request.data.get('description', job.description)
            job.required_skills = request.data.get('required_skills', job.required_skills)
            job.experience_required = request.data.get('experience_required', job.experience_required)
            job.location = request.data.get('location', job.location)
            job.salary_range = request.data.get('salary_range', job.salary_range)
            job.status = request.data.get('status', job.status)
            
            job.save()
            
            return Response({'message': 'Job updated successfully'})
        except JobRole.DoesNotExist:
            return Response({'error': 'Job not found'}, status=404)
    
    def delete(self, request, job_id):
        """Delete a job role"""
        try:
            job = JobRole.objects.get(id=job_id)
            job.delete()
            return Response({'message': 'Job deleted successfully'})
        except JobRole.DoesNotExist:
            return Response({'error': 'Job not found'}, status=404)
            
