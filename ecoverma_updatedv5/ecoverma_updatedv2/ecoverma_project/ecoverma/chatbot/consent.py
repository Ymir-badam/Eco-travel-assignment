

from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect

from .models import UserConsent


def current_version():
    return getattr(settings, "PRIVACY_POLICY_VERSION", "1.0")


def has_consent(user):
    return user.is_authenticated and UserConsent.objects.filter(
        user=user, policy_version=current_version()
    ).exists()


def record_consent(user):
    return UserConsent.objects.get_or_create(user=user, policy_version=current_version())[0]


def _wrap(view, api):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not has_consent(request.user):
            if api:
                return JsonResponse({"error": "consent_required"}, status=403)
            return redirect("chatbot:consent")
        return view(request, *args, **kwargs)
    return wrapper


def consent_required(view):
    
    return _wrap(view, api=False)


def consent_required_api(view):
    
    return _wrap(view, api=True)
