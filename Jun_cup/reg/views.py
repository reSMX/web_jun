from django.shortcuts import render

def reg(request):
    return render(request, 'regs/reg.html')


def login(request):
    return render(request, 'regs/login.html')
