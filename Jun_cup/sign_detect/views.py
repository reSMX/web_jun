from django.shortcuts import render


def sign_detect(request):
    return render(request, 'sign_detect/sign_detect.html')
