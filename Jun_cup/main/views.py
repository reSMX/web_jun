from django.shortcuts import render

def home(request):
    return render(request, r'main\home.html')
