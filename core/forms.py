from django import forms
from .models import HealthLog
from django.contrib.auth.models import User
from .models import UserProfile

# 1. Health Log Form (For the dashboard)
class HealthLogForm(forms.ModelForm):
    class Meta:
        model = HealthLog
        fields = ['sleep_hours', 'water_intake', 'calories_intake', 'protein', 'carbs', 'fats', 'exercise_type', 'calories_burned']
        widgets = {
            'sleep_hours': forms.NumberInput(attrs={'placeholder': 'e.g., 7.5'}),
            'water_intake': forms.NumberInput(attrs={'placeholder': 'e.g., 8 glasses'}),
            'calories_intake': forms.NumberInput(attrs={'placeholder': 'e.g., 2000 kcal'}),
            'protein': forms.NumberInput(attrs={'placeholder': 'e.g., 150g'}),
            'carbs': forms.NumberInput(attrs={'placeholder': 'e.g., 250g'}),
            'fats': forms.NumberInput(attrs={'placeholder': 'e.g., 70g'}),
            'exercise_type': forms.TextInput(attrs={'placeholder': 'e.g., Running, Gym, Yoga'}),
            'calories_burned': forms.NumberInput(attrs={'placeholder': 'e.g., 500 kcal'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all'
            })

# 2. Basic Profile Update Form (Safe from FieldErrors)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all text-gray-700 font-medium'
            })


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['health_issues', 'issue_stage', 'medications']
        widgets = {
            'health_issues': forms.TextInput(attrs={'placeholder': 'e.g., Diabetes, Hypertension, PCOS'}),
            'issue_stage': forms.TextInput(attrs={'placeholder': 'e.g., Type 2, Mild, Stage 1'}),
            'medications': forms.TextInput(attrs={'placeholder': 'e.g., Metformin (500mg), None'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all text-gray-700 font-medium'
            })