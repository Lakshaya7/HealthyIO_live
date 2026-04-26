from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Sends reminder emails to users inactive for more than 3 days.'

    def handle(self, *args, **kwargs):
        # 1. Calculate the date exactly 3 days ago
        three_days_ago = timezone.now() - timedelta(days=3)
        
        # 2. Find users whose last login was BEFORE 3 days ago
        # (We exclude superusers/admins so you don't spam yourself during testing)
        inactive_users = User.objects.filter(last_login__lt=three_days_ago, is_superuser=False)
        
        count = 0
        for user in inactive_users:
            if user.email:
                subject = "We miss you at HealthyIO! 🌱"
                message = f"Hi {user.first_name or user.username},\n\nYou haven't logged your health data in a few days. Consistency is key to achieving your wellness goals!\n\nLog in today to keep your streak alive and let our AI coach guide you.\n\nBest,\nThe HealthyIO Team"
                
                try:
                    send_mail(
                        subject,
                        message,
                        None, # Automatically uses DEFAULT_FROM_EMAIL from settings.py
                        [user.email],
                        fail_silently=False,
                    )
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"Sent reminder email to {user.email}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send to {user.email}. Error: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Task Complete: Successfully sent {count} reminder emails."))