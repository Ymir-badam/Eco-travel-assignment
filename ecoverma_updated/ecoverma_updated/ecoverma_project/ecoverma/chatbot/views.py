import json
import os

from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import consent as consent_utils
from .consent import consent_required, consent_required_api
from .forms import SignUpForm
from .models import CarbonCalculation, Message, VehicleLeg
from .router import get_conversation, process_message, start_new_conversation
from .services import carbon as carbon_service
from .services import retention


def home(request):
    return render(request, "chatbot/home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("chatbot:chat")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            consent_utils.record_consent(user) 
            auth_login(request, user)
            return redirect("chatbot:chat")
    else:
        form = SignUpForm()

    return render(
        request,
        "chatbot/signup.html",
        {"form": form, "retention_days": retention.retention_days()},
    )


@login_required(login_url="chatbot:login")
@consent_required
def chat(request, conversation_id=None):
    conversation = get_conversation(request, conversation_id=conversation_id)
    history = conversation.messages.all()
    conversations = request.user.conversations.all()
    return render(
        request,
        "chatbot/chat.html",
        {
            "conversation": conversation,
            "history": history,
            "conversations": conversations,
        },
    )


@login_required(login_url="chatbot:login")
@consent_required
@require_POST
def new_conversation(request):
    start_new_conversation(request)
    return redirect("chatbot:chat")


@login_required(login_url="chatbot:login")
@consent_required_api
@require_POST
def chat_api(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = data.get("message", "").strip()

    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)

    conversation = get_conversation(request)

    Message.objects.create(
        conversation=conversation,
        sender=Message.SENDER_USER,
        text=message,
    )

    result = process_message(request, message)

    Message.objects.create(
        conversation=conversation,
        sender=Message.SENDER_BOT,
        text=result.get("text", ""),
        links=result.get("links") or [],
    )

    return JsonResponse(result)


@login_required(login_url="chatbot:login")
@consent_required_api
@require_POST
def carbon_api(request):
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    raw_legs = data.get("legs") or []
    if not raw_legs:
        return JsonResponse({"error": "At least one leg is required"}, status=400)

    conversation = get_conversation(request)

    calculation = CarbonCalculation.objects.create(
        conversation=conversation,
        user=request.user if request.user.is_authenticated else None,
    )

    legs_out = []
    total_kg = 0.0

    for raw_leg in raw_legs:
        vehicle_type = raw_leg.get("vehicle_type")
        distance_raw = raw_leg.get("distance_km")

        try:
            distance_km = float(distance_raw)
        except (TypeError, ValueError):
            continue

        if vehicle_type not in carbon_service.EMISSION_FACTORS or distance_km <= 0:
            continue

        emission_kg = carbon_service.estimate_kg(vehicle_type, distance_km)

        VehicleLeg.objects.create(
            calculation=calculation,
            vehicle_type=vehicle_type,
            distance_km=distance_km,
            emission_kg=emission_kg,
        )

        total_kg += emission_kg
        legs_out.append(
            {
                "vehicle_type": vehicle_type,
                "label": carbon_service.VEHICLE_LABELS[vehicle_type],
                "distance_km": distance_km,
                "emission_kg": round(emission_kg, 1),
            }
        )

    if not legs_out:
        calculation.delete()
        return JsonResponse({"error": "No valid legs supplied"}, status=400)

    best_leg = min(legs_out, key=lambda leg: leg["emission_kg"])
    calculation.total_emission_kg = total_kg
    calculation.best_mode = best_leg["vehicle_type"]
    calculation.save()

    band = carbon_service.emission_band(total_kg)
    summary_text = (
        f"About {round(total_kg)} kg CO2e in total across {len(legs_out)} leg(s) "
        f"({band} for a single trip). Figures are rounded averages, not exact measurements."
    )

    result = {
        "text": summary_text,
        "action": "carbon_result",
        "legs": legs_out,
        "total_kg": round(total_kg, 1),
        "band": band,
        "best_mode": carbon_service.VEHICLE_LABELS.get(best_leg["vehicle_type"]),
    }

    Message.objects.create(
        conversation=conversation,
        sender=Message.SENDER_USER,
        text="Estimate carbon footprint: "
        + ", ".join(f"{leg['label']} ({leg['distance_km']} km)" for leg in legs_out),
    )
    Message.objects.create(
        conversation=conversation,
        sender=Message.SENDER_BOT,
        text=summary_text,
    )

    return JsonResponse(result)


def _privacy_context():
    return {
        "retention_days": retention.retention_days(),
        "policy_version": consent_utils.current_version(),
        "contact_email": os.environ.get("SERVICE_CONTACT_EMAIL", ""),
    }


def privacy(request):
    
    context = _privacy_context()
    context["deleted"] = request.GET.get("deleted")
    return render(request, "chatbot/privacy.html", context)


@login_required(login_url="chatbot:login")
def consent(request):
    
    if consent_utils.has_consent(request.user):
        return redirect("chatbot:chat")

    error = False
    if request.method == "POST":
        if request.POST.get("consent") == "on":
            consent_utils.record_consent(request.user)
            return redirect("chatbot:chat")
        error = True

    context = _privacy_context()
    context["error"] = error
    return render(request, "chatbot/consent.html", context)


@login_required(login_url="chatbot:login")
@require_POST
def delete_my_conversations(request):
    
    request.user.conversations.all().delete()
    request.user.carbon_calculations.all().delete()
    request.session.pop("active_conversation_id", None)
    return redirect(reverse("chatbot:privacy") + "?deleted=1")


@login_required(login_url="chatbot:login")
@require_POST
def delete_account(request):
    
    user = request.user
    user.conversations.all().delete()
    user.carbon_calculations.all().delete()
    auth_logout(request)
    user.delete()  
    return redirect("chatbot:home")
