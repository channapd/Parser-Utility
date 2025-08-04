from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import CustomUser  

def login(request):
    if request.method == 'POST':  
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "Invalid Email")
            return redirect('authApp:login')
        
        if user.check_password(password):
            auth_login(request, user)
            if user.is_staff:
                return redirect('mainApp:admin_home')
            return redirect('mainApp:home')  
        else:
            messages.error(request, "Invalid Email or Password.")
            return redirect('authApp:login')
        
    return render(request, "authApp/login.html")


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        company = request.POST.get('company')
        password = request.POST.get('password')
        rePassword = request.POST.get('rePassword')
        if password == rePassword:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email is already registered.')
                return redirect('authApp:register')
            else:
                user = CustomUser.objects.create_user(username=username, email=email, company=company, password=password)
                user.save()
                messages.success(request, 'Registration successful. Please log in.')
                return redirect('authApp:login')
        else:
            messages.error(request, 'Passwords do not match.')
            return redirect('authApp:register')
        
    return render(request, "authApp/register.html")


def admin_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        company = request.POST.get('company')
        user_type = request.POST.get('user_type')  
        password = request.POST.get('password')
        rePassword = request.POST.get('rePassword')

        if password != rePassword:
            messages.error(request, 'Passwords do not match.')
            return redirect('authApp:admin_register')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email is already registered.')
            return redirect('authApp:admin_register')

        is_staff = True if user_type == 'admin' else False

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            company=company,
            password=password,
        )
        user.is_staff = is_staff
        user.save()

        messages.success(request, 'Successfully Registered User')
        return redirect('mainApp:admin_home')

    return render(request, "authApp/admin_register.html")



def logout_user(request):
    logout(request)
    return redirect("authApp:login")
