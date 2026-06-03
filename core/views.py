from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from module_manager.models import AvailableApp


def home_view(request: HttpRequest):
    return render(request, "home.html")


@login_required
def welcome_view(request: HttpRequest):
    """Wizard de primer arranque."""
    installed_count = AvailableApp.objects.filter(is_installed=True).count()
    return render(
        request,
        "welcome.html",
        {"installed_count": installed_count},
    )


@login_required
def welcome_dismiss(request: HttpRequest):
    """Marca el welcome como visto para esta sesión y redirige al hub."""
    request.session["welcome_dismissed"] = True
    return redirect("get_apps")


@login_required
def account_view(request: HttpRequest):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Mantener la sesión activa después del cambio.
            update_session_auth_hash(request, form.user)
            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect("account")
        messages.error(request, "Revisa los errores del formulario.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, "account.html", {"password_form": form})


def health_view(request: HttpRequest):
    """
    Endpoint público sin auth: usado por el healthcheck de Docker y por
    monitores externos. No revela información sensible.
    """
    try:
        plugins_count = AvailableApp.objects.count()
        db_ok = True
    except Exception:
        plugins_count = None
        db_ok = False

    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": settings.QUEAI_VERSION or "unknown",
        "debug": settings.DEBUG,
        "plugins": plugins_count,
    }
    return JsonResponse(payload, status=200 if db_ok else 503)
