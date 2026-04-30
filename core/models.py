from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json
import re
import os
from groq import Groq

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    health_issues = models.CharField(max_length=255, null=True, blank=True)
    issue_stage = models.CharField(max_length=100, null=True, blank=True)
    medications = models.CharField(max_length=255, null=True, blank=True)

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    
    # We use Date of Birth instead of 'Age' so the age automatically updates every year
    date_of_birth = models.DateField(blank=True, null=True, help_text="Used to calculate exact age")
    
    # Menstrual cycle tracking (Hidden on front-end for non-females)
    last_menstrual_period = models.DateField(blank=True, null=True, help_text="Leave blank if not applicable")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class HealthLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    sleep_hours = models.FloatField(null=True, blank=True)
    water_intake = models.FloatField(null=True, blank=True)
    calories_intake = models.FloatField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    carbs = models.FloatField(null=True, blank=True)
    fats = models.FloatField(null=True, blank=True)
    exercise_type = models.CharField(max_length=100, null=True, blank=True)
    calories_burned = models.FloatField(null=True, blank=True)
    health_score = models.FloatField(null=True, blank=True)
    suggestion = models.TextField(null=True, blank=True)

    def calculate_score(self):
        api_key = os.environ.get('GROQ_API_KEY', '')
        
        # Pull the user's medical context
        try:
            profile = self.user.userprofile
            med_context = f"Conditions: {profile.health_issues or 'None'}. Stage: {profile.issue_stage or 'N/A'}. Meds: {profile.medications or 'None'}."
        except:
            med_context = "No medical history provided."

        prompt = f"""Evaluate this daily health log (Score 0-100 and a 1-sentence suggestion).
        USER MEDICAL PROFILE: {med_context}
        Sleep: {self.sleep_hours}, Water: {self.water_intake}, Cal In: {self.calories_intake}, Out: {self.calories_burned}.
        CRITICAL: Adjust the score and suggestion strictly based on their medical conditions (e.g., recommend water for kidney issues, penalize heavy carbs if diabetic).
        Respond ONLY as JSON: {{ "score": 85, "suggestion": "Text" }}"""
        
        try:
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
            )
            raw = response.choices[0].message.content
            cleaned = re.sub(r'```json\n|\n```|```', '', raw).strip()
            data = json.loads(cleaned)
            self.health_score = float(data.get('score', 50))
            self.suggestion = data.get('suggestion', 'Good job!')
        except Exception as e:
            print(f"AI Score Error: {e}")
            self.health_score = 50.0
            self.suggestion = "AI Analysis failed."