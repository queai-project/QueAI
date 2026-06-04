from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from module_manager.models import AvailableApp

from .models import AuditEvent


def home_view(request: HttpRequest):
    # 1) Sin auth: a /login/. Pasamos SIN ?next= a propósito para que Django
    #    use LOGIN_REDIRECT_URL (/welcome/), no nos devuelva aquí saltándose
    #    el onboarding.
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL)
    # 2) Con auth pero sin haber dismisseado el welcome: al onboarding.
    #    Sin esto, un usuario que llegue a / por bookmark/manual nunca pasa
    #    por el welcome.
    if not request.session.get("welcome_dismissed"):
        return redirect("welcome")
    # 3) Auth + welcome ya visto: home normal con las nav-cards.
    return render(request, "home.html")


@login_required
def welcome_view(request: HttpRequest):
    """Wizard de primer arranque.

    Si el usuario ya dismisseó esta sesión, vamos directos al hub —
    el welcome es un onboarding, no algo que ver dos veces seguidas.
    Si quiere volver a verlo, /welcome/?force=1 lo fuerza.
    """
    if request.session.get("welcome_dismissed") and not request.GET.get("force"):
        return redirect("get_apps")
    installed_count = AvailableApp.objects.filter(is_installed=True).count()
    return render(
        request,
        "welcome.html",
        {"installed_count": installed_count},
    )


@login_required
def welcome_dismiss(request: HttpRequest):
    """Marca el welcome como visto y vuelve al home — desde ahí el
    usuario decide a qué sección quiere ir."""
    request.session["welcome_dismissed"] = True
    return redirect("home")


@login_required
def audit_view(request: HttpRequest):
    """Tabla de audit log con filtros + paginación."""
    qs = AuditEvent.objects.select_related("user")

    action = request.GET.get("action", "").strip()
    target = request.GET.get("target", "").strip()
    source = request.GET.get("source", "").strip()
    only_failures = request.GET.get("only_failures") == "1"

    if action:
        qs = qs.filter(action=action)
    if target:
        qs = qs.filter(target__icontains=target)
    if source:
        qs = qs.filter(source=source)
    if only_failures:
        qs = qs.filter(success=False)

    paginator = Paginator(qs, 40)
    page = paginator.get_page(request.GET.get("page") or 1)

    return render(
        request,
        "audit.html",
        {
            "page": page,
            "filters": {"action": action, "target": target, "source": source, "only_failures": only_failures},
            "actions_choices": ["install", "start", "stop", "uninstall", "delete", "save_env", "download"],
            "sources_choices": [c[0] for c in AuditEvent.SOURCE_CHOICES],
            "total": paginator.count,
        },
    )


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
