from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Avg, Count
from .models import HealthLog, UserProfile
from .forms import HealthLogForm, UserUpdateForm, UserProfileForm
from django.db.models import Avg, Sum
import io
from django.http import FileResponse
from django.utils import timezone
import threading
import os
import json
import re
from groq import Groq
from datetime import date, timedelta

# --- Helper for Clean AI Initialization ---
def get_ai_client():
    """Returns a clean Groq client without proxy conflicts."""
    api_key = os.environ.get('GROQ_API_KEY', '')
    # Initializing without extra kwargs to avoid 'proxies' error
    return Groq(api_key=api_key)

# --- PUBLIC VIEWS ---

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def tips(request):
    tips_list = [
        {"icon": "droplet", "color": "blue", "title": "Stay Hydrated", "desc": "Drink at least 8 glasses (2 liters) of water daily. Dehydration impacts focus and energy."},
        {"icon": "moon", "color": "purple", "title": "Optimize Sleep", "desc": "Aim for 7-9 hours of quality sleep. Keep your room dark and avoid screens 1 hour before bed."},
        {"icon": "activity", "color": "teal", "title": "Daily Movement", "desc": "Even a 20-minute brisk walk can significantly lower cardiovascular risk and boost mood."},
        {"icon": "apple", "color": "red", "title": "Eat Whole Foods", "desc": "Prioritize single-ingredient foods. Aim for lean proteins, healthy fats, and complex carbs."},
        {"icon": "sun", "color": "yellow", "title": "Morning Sun", "desc": "Get 10-15 mins of sunlight in your eyes upon waking to set your circadian rhythm."},
        {"icon": "brain", "color": "indigo", "title": "Mental Reset", "desc": "Practice 5 minutes of mindful breathing daily to drastically reduce cortisol (stress) levels."}
    ]
    return render(request, 'core/tips.html', {'tips': tips_list})

# --- PROTECTED VIEWS ---

@login_required
def profile(request):
    from django.contrib import messages
    from .models import UserProfile
    from .forms import UserProfileForm
    
    # Ensure profile exists to prevent crashes
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Save Identity fields (Name)
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        # Save Biological and Medical Data (Form)
        form = UserProfileForm(request.POST, instance=profile_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile saved successfully!")
    else:
        form = UserProfileForm(instance=profile_obj)
        
    return render(request, 'core/profile.html', {'form': form})


@login_required
def dashboard(request):
    logs = HealthLog.objects.filter(user=request.user).order_by('-date', '-id')
    latest_log = logs.first()
    
    latest_suggestion = "Log your data today to get your AI feedback!"
    latest_score = 0
    
    if latest_log:
        if latest_log.suggestion:
            latest_suggestion = latest_log.suggestion
        latest_score = latest_log.health_score or 0

    avg_score_data = logs.aggregate(Avg('health_score'))
    avg_health_score = avg_score_data['health_score__avg'] or 0
    avg_sleep_data = logs.aggregate(Avg('sleep_hours'))
    avg_sleep = avg_sleep_data['sleep_hours__avg'] or 0
    total_workouts = sum(1 for log in logs if log.exercise_type and log.exercise_type.lower() not in ['none', '', 'null'])

    context = {
        'logs': logs,
        'latest_log': latest_log,
        'latest_suggestion': latest_suggestion,
        'latest_score': latest_score,
        'user': request.user, 
        'avg_health_score': round(avg_health_score, 1), 
        'avg_sleep': round(avg_sleep, 1),
        'total_workouts': total_workouts,
    }
    return render(request, 'core/dashboard.html', context)

# --- SUB-MODULES & TOOLS ---

@login_required
def add_log(request):
    if request.method == 'POST':
        form = HealthLogForm(request.POST)
        if form.is_valid():
            new_log = form.save(commit=False)
            new_log.user = request.user
            new_log.save() # Save first to get an ID
            
            # Calculate AI score and suggestion
            new_log.calculate_score()
            new_log.save() # Save again to store the AI's results
            
            # FIX: Instead of returning redirect('dashboard'), we re-render the 
            # add_log page and pass show_modal=True and the result to trigger the popup!
            return render(request, 'core/add_log.html', {
                'form': HealthLogForm(), # Pass a fresh empty form for the background
                'show_modal': True,
                'result': new_log,
                'is_edit': False
            })
    else:
        form = HealthLogForm()
        
    return render(request, 'core/add_log.html', {'form': form, 'is_edit': False})

@login_required
def edit_log(request, log_id):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from .models import HealthLog
    from .forms import HealthLogForm

    log = get_object_or_404(HealthLog, id=log_id, user=request.user)
    
    if request.method == 'POST':
        form = HealthLogForm(request.POST, instance=log)
        if form.is_valid():
            updated_log = form.save(commit=False)
            updated_log.calculate_score() # Recalculate AI score with edited data
            updated_log.save()
            messages.success(request, "Log updated successfully!")
            return redirect('dashboard')
    else:
        form = HealthLogForm(instance=log)
        
    # Re-use the add_log template, but pass is_edit=True so it changes titles and hides the modal
    return render(request, 'core/add_log.html', {
        'form': form, 
        'is_edit': True,
        'show_modal': False 
    })


@login_required
def delete_log(request, log_id):
    from django.shortcuts import get_object_or_404
    log = get_object_or_404(HealthLog, id=log_id, user=request.user)
    log.delete()
    messages.success(request, "Log deleted successfully!")
    return redirect('dashboard')


@login_required
def game(request):
    return render(request, 'core/game.html')

@login_required
def food_search(request):
    data = None
    if request.method == 'POST':
        food_query = request.POST.get('food_query', '')
        
        from django.db.models import Avg
        logs = HealthLog.objects.filter(user=request.user)
        stats = logs.aggregate(avg_score=Avg('health_score'), avg_calories=Avg('calories_intake'))
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        
        user_context = f"""
        USER LIFETIME STATS:
        - Avg Health Score: {stats['avg_score'] or 'N/A'}
        
        MEDICAL CONTEXT (CRITICAL):
        - Health Issues: {profile_obj.health_issues or 'None reported'}
        - Stage/Severity: {profile_obj.issue_stage or 'N/A'}
        - Medications: {profile_obj.medications or 'None reported'}
        """

        prompt = f"""Provide a clinical nutritional analysis for 100g of "{food_query}".
        {user_context}
        
        Based strictly on their MEDICAL CONTEXT, is this food safe? Will it interact with their medications?
        
        Output ONLY a JSON object with EXACT keys:
        - food_name: string
        - health_score: number (0-100)
        - glycemic_index: number
        - opinion: string (Detailed advice strictly tailored to their medical issues and meds)
        - quantity_advice: string (Safe serving size considering their health issues)
        - fitness_impact: string
        - satiety_index: string
        - micronutrients: list of strings
        - fiber: string
        - hydration: string
        - calories: number, protein: number, carbs: number, fats: number
        - summary: string
        """
        
        try:
            client = get_ai_client()
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.2,
            )
            raw = response.choices[0].message.content
            import re, json
            cleaned = re.sub(r'```json\n|\n```|```', '', raw).strip()
            data = json.loads(cleaned)
        except Exception as e:
            messages.error(request, "AI was unable to process the medical analysis.")
            
    return render(request, 'core/food_search.html', {'data': data})

# ... existing code (ai_coach stays the same) ...


# ... your existing views ...

@login_required
def scripty_log(request):
    if request.method == 'POST':
        scripty_text = request.POST.get('scripty_text', '')
        
        # 1. Upgraded Prompt: Provide an exact JSON template to force the AI to use the right keys
        prompt = f"""Extract the health data from this text: "{scripty_text}".
        Respond with ONLY a valid JSON object exactly matching this structure. Use raw numbers only (no text, no 'kcal'):
        {{
            "sleep_hours": 0,
            "water_intake": 0,
            "calories_intake": 0,
            "exercise_type": "",
            "calories_burned": 0
        }}"""
        
        try:
            client = get_ai_client()
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
            )
            raw = response.choices[0].message.content
            cleaned = re.sub(r'```json\n|\n```|```', '', raw).strip()
            data = json.loads(cleaned)
            
            # 2. Bulletproof Extractor: Forces any weird AI responses like "2000 kcal" into clean numbers
            def safe_float(val):
                if not val: return 0.0
                val_str = str(val).replace(',', '') # Remove commas like 2,000
                nums = re.findall(r'\d+\.?\d*', val_str)
                return float(nums[0]) if nums else 0.0
            
            # 3. Map the exact keys to the database fields safely
            new_log = HealthLog(
                user=request.user,
                sleep_hours=safe_float(data.get('sleep_hours')),
                water_intake=safe_float(data.get('water_intake')),
                calories_intake=safe_float(data.get('calories_intake')),
                exercise_type=str(data.get('exercise_type') or "").strip(),
                calories_burned=safe_float(data.get('calories_burned')),
            )
            
            # 4. Trigger the AI score calculation and save!
            new_log.calculate_score()
            new_log.save()
            
            messages.success(request, "ScripTy successfully analyzed and logged your day!")
        except Exception as e:
            messages.error(request, f"ScripTy encountered an error: {e}")
            
    return redirect('dashboard')

@login_required
def download_report(request):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
    except ImportError:
        messages.error(request, "PDF Library missing. Please run: pip install reportlab")
        return redirect('dashboard')

    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title & Header
    p.setFont("Helvetica-Bold", 24)
    p.setFillColorRGB(0.05, 0.58, 0.53)  # Teal color
    p.drawString(50, height - 60, "HealthyIO - Personal Health Report")

    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(50, height - 90, f"User: {request.user.username} | Date: {timezone.now().strftime('%B %d, %Y')}")
    
    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(50, height - 100, width - 50, height - 100)

    # Fetch User Stats
    logs = HealthLog.objects.filter(user=request.user).order_by('-date')
    
    # Safely cast database averages to float to prevent SQLite TypeErrors
    avg_score = float(logs.aggregate(Avg('health_score'))['health_score__avg'] or 0)
    avg_sleep = float(logs.aggregate(Avg('sleep_hours'))['sleep_hours__avg'] or 0)
    avg_intake = float(logs.aggregate(Avg('calories_intake'))['calories_intake__avg'] or 0)
    avg_burned = float(logs.aggregate(Avg('calories_burned'))['calories_burned__avg'] or 0)
    total_logs = logs.count()

    # Averages Section
    p.setFont("Helvetica-Bold", 16)
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.drawString(50, height - 140, "Lifetime Averages:")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 165, f"• Average Health Score: {round(avg_score, 1)} / 100")
    p.drawString(50, height - 185, f"• Average Sleep: {round(avg_sleep, 1)} hours/night")
    p.drawString(50, height - 205, f"• Average Calorie Intake: {round(avg_intake)} kcal/day")
    p.drawString(50, height - 225, f"• Average Calories Burned: {round(avg_burned)} kcal/day")
    p.drawString(50, height - 245, f"• Total Entries Recorded: {total_logs}")

    # Recent History Table Header (Shifted down to make room for new averages)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 290, "Recent History (Last 10 Entries):")

    y = height - 320
    p.setFont("Helvetica-Bold", 11)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    
    # Adjusted columns to fit the detailed calorie breakdown
    p.drawString(50, y, "Date")
    p.drawString(130, y, "Sleep")
    p.drawString(190, y, "Water")
    p.drawString(260, y, "Calories (In / Out)")
    p.drawString(450, y, "Score")
    
    p.line(50, y - 5, width - 50, y - 5)

    # Recent History Data
    p.setFont("Helvetica", 11)
    p.setFillColorRGB(0.2, 0.2, 0.2)
    for log in logs[:10]:
        y -= 25
        # Prevent drawing off the page
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
            
        # Safely cast individual values to float
        sleep_val = float(log.sleep_hours or 0)
        water_val = float(log.water_intake or 0)
        intake_val = float(log.calories_intake or 0)
        burned_val = float(log.calories_burned or 0)
        score_val = float(log.health_score or 0)
        
        # Display accurate detailed values instead of an obscured "Net" value
        log_date_str = f"{log.date}" if log.date else "N/A"
        p.drawString(50, y, log_date_str)
        p.drawString(130, y, f"{round(sleep_val, 1)} hrs")
        p.drawString(190, y, f"{round(water_val, 1)} gls")
        p.drawString(260, y, f"{round(intake_val)} In / {round(burned_val)} Out")
        
        # Color code the score text in the PDF
        score_rounded = round(score_val)
        if score_rounded >= 75: p.setFillColorRGB(0.1, 0.7, 0.3) # Green
        elif score_rounded >= 50: p.setFillColorRGB(0.8, 0.6, 0.1) # Yellow
        else: p.setFillColorRGB(0.9, 0.2, 0.2) # Red
        
        p.drawString(450, y, f"{score_rounded}")
        p.setFillColorRGB(0.2, 0.2, 0.2) # Reset color for next row

    # Save PDF
    p.showPage()
    p.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename=f"HealthyIO_Report_{request.user.username}.pdf")

@login_required
def ai_coach(request):
    import os
    from groq import Groq
    import re
    from datetime import date, timedelta
    
    ai_response = None
    error = None
    
    try:
        profile = request.user.userprofile
        
        # 1. Age Calculation
        age_context = "Age not provided."
        if profile.date_of_birth:
            today = date.today()
            age = today.year - profile.date_of_birth.year - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
            age_context = f"User is {age} years old."
            
        # 2. Cycle Calculation
        cycle_context = ""
        if profile.gender == 'F' and profile.last_menstrual_period:
            next_cycle = profile.last_menstrual_period + timedelta(days=28)
            cycle_context = f"Female. Last period: {profile.last_menstrual_period}. Next predicted: {next_cycle}. Adapt mood/fitness advice to this."

        # 3. Master Medical Context
        med_context = f"""
        CLINICAL DATA:
        - Health Issues: {profile.health_issues or 'None'}
        - Stage/Severity: {profile.issue_stage or 'N/A'}
        - Medications: {profile.medications or 'None'}
        
        BIOLOGICAL DATA:
        - {age_context}
        - Gender: {profile.get_gender_display() or 'N/A'}
        - {cycle_context}
        """
        
        logs = HealthLog.objects.filter(user=request.user).order_by('-date')[:7]
        log_text = "\n".join([f"{l.date}: Sleep {l.sleep_hours}h, Water {l.water_intake} glasses, Exercise {l.exercise_type} ({l.calories_burned} kcal), Diet: In {l.calories_intake}kcal" for l in logs])

        prompt = f"""
        Act as an elite medical & lifestyle AI coach. 
        Read this user's profile carefully and tailor EVERY piece of advice around their conditions and medications.
        
        USER PROFILE:
        {med_context}
        
        LAST 7 DAYS OF LOGS:
        {log_text}
        
        Provide a structured, empathetic analysis. Use HTML formatting (<h3>, <ul>, <li>, <strong>) for readability. Do NOT use markdown.
        """

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        ai_response = response.choices[0].message.content
        
    except Exception as e:
        error = f"Coach is currently unavailable. Error: {str(e)}"
        
    return render(request, 'core/ai_analysis.html', {'ai_response': ai_response, 'error': error})


@login_required
def healy_chat(request):
    import json
    from django.http import JsonResponse
    from groq import Groq
    import os

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # Healy's Strict System Prompt
            system_prompt = """
            You are Healy, a friendly, supportive, and highly knowledgeable AI health and fitness assistant for the HealthyIO app.
            
            CRITICAL RULES:
            1. ONLY answer questions related to health, fitness, nutrition, medicine, mental wellness, and exercise.
            2. If the user asks about ANYTHING else (e.g., coding, politics, movies, math, random chat), you MUST politely decline and say: "I am Healy, your dedicated health assistant. I can only help you with health, nutrition, and fitness topics!"
            3. Keep your answers concise, practical, and conversational. Do not write essays.
            4. Use simple HTML tags like <b>, <ul>, <li>, and <br> for formatting. Do NOT use markdown like ** or #.
            """

            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            response = client.chat.completions.create(
                model="llama3-8b-8192", # Fast and responsive model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3, # Low temperature keeps it focused on facts
            )
            
            ai_reply = response.choices[0].message.content
            return JsonResponse({'status': 'success', 'reply': ai_reply})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'reply': "I'm having a little trouble connecting to my servers right now. Let's try again in a moment!"})
            
    return JsonResponse({'status': 'error', 'reply': 'Invalid request'})