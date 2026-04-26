from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .models import UserProfile

@receiver(post_save, sender=User)
def create_profile_and_send_email(sender, instance, created, **kwargs):
    if created:
        # 1. Automatically create the UserProfile to prevent dashboard crashes
        UserProfile.objects.create(user=instance)
        
        # 2. Automatically send the Welcome Email (if they provided an email)
        if instance.email:
            subject = 'Welcome to HealthyIO! 🌱'
            message = f'''Hi {instance.first_name or instance.username},

Welcome to HealthyIO! We are thrilled to have you join our community. 

Your AI health coach is ready and waiting to help you optimize your sleep, nutrition, and daily habits. Log in today to submit your first daily health log!

Stay Healthy,
The HealthyIO Team'''
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.email],
                    fail_silently=True, # Prevents site from crashing if email fails
                )
            except Exception as e:
                print(f"Error sending email: {e}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Saves the profile whenever the user object is saved
    instance.userprofile.save()