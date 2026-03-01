from django.http import HttpResponse, HttpRequest


def home_view(request: HttpRequest):
    return HttpResponse("<h2>Welcome to the Home Page</h2><p>This is a simple Django application.</p><button onclick=\"location.href='/store/'\">Go to App Store</button>")