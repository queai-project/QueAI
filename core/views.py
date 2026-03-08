from django.http import HttpRequest
from django.shortcuts import render


def home_view(request: HttpRequest):
    return render(request, "home.html")
