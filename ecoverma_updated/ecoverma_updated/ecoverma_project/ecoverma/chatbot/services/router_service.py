

from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional
import logging
import random
import re

from . import attractions as attractions_service
from . import carbon as carbon_service
from . import currency as currency_service
from . import geocode as geocode_service
from . import hotels as hotels_service
from . import place_description as place_description_service
from . import transport as transport_service
from .hotels import ECO_PROXY_DISCLAIMER

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.60
MAX_FALLBACKS_BEFORE_HANDOVER = 2

REQUIRED_SLOTS = ["destination", "dates", "budget", "sustainability_level"]

SLOT_QUESTIONS = {
    "destination": [
        "Where would you like to travel?",
        "Which destination are you dreaming about?",
        "What's the destination for this trip?",
    ],
    "dates": [
        "When are you planning to travel?",
        "Do you have travel dates in mind?",
        "What time of year are you thinking of going?",
    ],
    "budget": [
        "What's your approximate budget?",
        "Roughly how much are you looking to spend?",
        "Do you have a budget in mind for this trip?",
    ],
    "sustainability_level": [
        "Do you have a sustainability preference — for example "
        "low-carbon travel, eco-certified stays, or no particular preference?",
        "How important is sustainability for this trip — low-carbon travel, "
        "eco-certified stays, or no strong preference either way?",
        "Any sustainability priorities I should plan around — low-carbon "
        "transport, certified-green hotels, or not a big factor for you?",
    ],
}

RESPONSES: Dict[str, List[str]] = {
    "greet": [
        "Hello! I can help you plan a sustainable trip. Where would you like to go?",
        "Hi there! 🌿 Ready to plan a low-carbon trip? Where are you headed?",
        "Hey! I'm your EcoTravel Advisor — tell me where you'd like to go and I'll take it from there.",
    ],
    "goodbye": [
        "Goodbye! Have a great trip.",
        "Safe travels! Come back any time you want to plan another trip.",
        "Bye for now — happy (and sustainable) travels!",
    ],
    "thank": [
        "You're welcome!",
        "Anytime — happy to help.",
        "Glad I could help!",
    ],
    "affirm": [
        "Great!",
        "Perfect.",
        "Awesome, let's keep going.",
    ],
    "deny": [
        "No problem.",
        "Understood.",
        "That's alright — let me know what you'd prefer instead.",
    ],
    "ack_destination": [
        "Great — {destination} sounds interesting.",
        "{destination} is a lovely choice.",
        "Nice pick — {destination} it is.",
    ],
    "ack_dates": [
        "Got it, I've noted your travel dates.",
        "Noted those dates, thanks.",
        "Thanks, I've got your travel dates down.",
    ],
    "ack_budget": [
        "Got it — budget of {budget} {currency}.",
        "Noted, {budget} {currency} to work with.",
        "Thanks — I'll plan around {budget} {currency}.",
    ],
    "ack_sustainability": [
        "Got it, I'll keep that preference in mind.",
        "Noted — I'll factor that into what I suggest.",
        "Thanks, I'll weigh that in the recommendations.",
    ],
    "fallback": [
        "Sorry, I didn't quite understand that. You can ask about "
        "hotels, transport, attractions, weather, or carbon footprint.",
        "I'm not sure I follow — try asking about hotels, transport, "
        "attractions, weather, or your carbon footprint.",
        "Hmm, that one didn't land. I can help with hotels, transport, "
        "attractions, weather, or estimating your carbon footprint.",
    ],
    "handover": [
        "I'm having trouble understanding what you need. I'm connecting "
        "you with a human travel advisor.",
        "I don't want to keep guessing — let me hand you over to a human "
        "travel advisor.",
    ],
    "hotels_geocode_fail": [
        "I couldn't pin down {destination} on the map — could you try a "
        "nearby larger town or check the spelling?",
    ],
    "hotels_empty": [
        "I couldn't find hotel listings for {destination} right now — the "
        "map data source may be sparse there or briefly unavailable.",
    ],
    "hotels_intro": [
        "Here are hotels near {destination}.",
        "A few hotel options near {destination}:",
        "Found some places to stay near {destination}.",
    ],
    "transport_geocode_fail": [
        "I couldn't pin down {destination} on the map.",
    ],
    "transport_intro": [
        "Public transport near {destination} is {verdict}.",
        "For getting around {destination}: public transport is {verdict}.",
    ],
    "attractions_geocode_fail": [
        "I couldn't pin down {destination} on the map.",
    ],
    "attractions_empty": [
        "I couldn't find listed museums or historic sites near {destination} right now.",
    ],
    "attractions_intro": [
        "A few cultural sites near {destination}:",
        "Worth visiting near {destination}:",
        "Here's what's worth seeing near {destination}:",
    ],
    "weather_geocode_fail": [
        "I couldn't pin down {destination} on the map.",
    ],
    "weather_unavailable": [
        "I couldn't reach the weather service for {destination} just now — please try again shortly.",
    ],
    "itinerary_intro": [
        "{intro}I've got everything I need — {summary}. Here's what I found:",
        "{intro}All set — {summary}. Here's your plan:",
        "{intro}Thanks for all that — {summary}. Here's what I put together:",
    ],
    "itinerary_geocode_fail": [
        "I've got your preferences, but I couldn't locate \"{destination}\" "
        "on the map. Could you try a nearby larger town, or check the spelling?",
    ],
}


def pick(key: str, **kwargs) -> str:
    """Random line for `key`, formatted with kwargs."""
    template = random.choice(RESPONSES[key])
    return template.format(**kwargs)


def pick_slot_question(slot: str) -> str:
    return random.choice(SLOT_QUESTIONS[slot])

ENTITY_FIELD_MAP = {
    "destination": "destination",
    "dates": "dates",
    "budget": "budget",
    "currency": "currency",
    "sustainability_level": "sustainability_level",
}

ACTION_REQUIRED_SLOTS = {
    "find_hotels": ["destination"],
    "find_transport": ["destination"],
    "find_attractions": ["destination"],
    "weather_forecast": ["destination"],
}



def get_all_entity_values(entities: List[dict], entity_name: str) -> List[Any]:
    """Return every value tagged with this entity name (not just the first)."""
    return [
        e.get("value")
        for e in entities
        if e.get("entity") == entity_name and e.get("value") is not None
    ]


def get_entity(entities: List[dict], entity_name: str) -> Optional[Any]:
    """Return the last (most recently stated) value for this entity name."""
    values = get_all_entity_values(entities, entity_name)
    return values[-1] if values else None


def parse_budget(raw: Any) -> Optional[Decimal]:
    """Turn '2,000', '$2000', '2000usd', 2000.5 etc. into a Decimal."""
    if raw is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(raw))
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _store_extra_entities(conversation, entities: List[dict]) -> None:
    """Persist entity types we don't have a named field for."""
    unmapped = [e for e in entities if e.get("entity") not in ENTITY_FIELD_MAP]
    if not unmapped:
        return

    store = conversation.extra_entities or {}
    for e in unmapped:
        name = e.get("entity")
        value = e.get("value")
        if name is None or value is None:
            continue
        store.setdefault(name, [])
        if value not in store[name]:
            store[name].append(value)

    conversation.extra_entities = store


def apply_entities(conversation, entities: List[dict]) -> None:
    """Update the conversation with every entity the NLU detected."""

    destination = get_entity(entities, "destination")
    if destination and destination != conversation.destination:
        conversation.destination = str(destination)
        conversation.destination_lat = None
        conversation.destination_lon = None

    dates = get_entity(entities, "dates")
    if dates:
        conversation.dates = str(dates)

    budget = parse_budget(get_entity(entities, "budget"))
    if budget is not None:
        conversation.budget = budget

    currency = get_entity(entities, "currency")
    if currency:
        conversation.currency = str(currency)

    sustainability = get_entity(entities, "sustainability_level")
    if sustainability:
        conversation.sustainability_level = str(sustainability)

    _store_extra_entities(conversation, entities)


def missing_slots(conversation, required: List[str] = REQUIRED_SLOTS) -> List[str]:
    """Which required slots are still empty, in priority order."""
    return [slot for slot in required if not getattr(conversation, slot, None)]


def _plan_summary(conversation) -> str:
    return (
        f"destination: {conversation.destination}, "
        f"dates: {conversation.dates}, "
        f"budget: {conversation.budget} {conversation.currency or ''}".strip() + ", "
        f"sustainability preference: {conversation.sustainability_level}"
    )


def _continue_trip_planning(conversation, acknowledgment: Optional[str] = None) -> dict:
    """
    Shared logic for every 'inform_*' / start_trip_planning intent:
    acknowledge what was just given, then ask for the next missing slot,
    resume whatever the user originally asked for, or - once every slot
    is filled and nothing is pending - build the full itinerary.
    """
    missing = missing_slots(conversation)

    if missing:
        next_slot = missing[0]
        question = pick_slot_question(next_slot)
        text = f"{acknowledgment} {question}".strip() if acknowledgment else question
        return {"text": text, "awaiting_slot": next_slot}

    resumed = _resume_pending_action(conversation)
    if resumed:
        return resumed

    intro = f"{acknowledgment} " if acknowledgment else ""
    itinerary_response = build_itinerary(conversation)
    if not itinerary_response.get("_skip_intro"):
        itinerary_response["text"] = pick(
            "itinerary_intro", intro=intro, summary=_plan_summary(conversation)
        )
    itinerary_response["slots_complete"] = True
    return itinerary_response


def _resume_pending_action(conversation) -> Optional[dict]:
    """If the user asked for hotels/transport/etc. before we had enough
    info, and we now do, run that action instead of making them re-ask."""
    if not conversation.pending_action:
        return None

    action = conversation.pending_action
    required = ACTION_REQUIRED_SLOTS.get(action, [])
    if missing_slots(conversation, required):
        return None  # still not enough info for that specific action

    conversation.pending_action = None
    conversation.save()
    return ACTION_RESPONSES.get(action, lambda c: None)(conversation)


def _require_slots_then(action_name: str, build_response: Callable[[Any], dict]):
    """
    Wrap an action handler (ask_hotels, ask_transport, ...) so that if a
    required slot is missing, the bot asks for it - and remembers to run
    the action automatically once the slot is filled.
    """
    def handler(conversation, entities):
        required = ACTION_REQUIRED_SLOTS.get(action_name, [])
        missing = missing_slots(conversation, required)
        if missing:
            next_slot = missing[0]
            conversation.pending_action = action_name
            conversation.save()
            return {"text": pick_slot_question(next_slot), "awaiting_slot": next_slot}
        return build_response(conversation)
    return handler



def _ensure_coordinates(conversation):
    """
    Make sure conversation.destination_lat/lon are set, geocoding (and
    persisting) them if not. Returns (lat, lon, display_name) or None.
    """
    if conversation.destination_lat is not None and conversation.destination_lon is not None:
        return conversation.destination_lat, conversation.destination_lon, conversation.destination

    result = geocode_service.geocode(conversation.destination)
    if not result:
        return None

    conversation.destination_lat = result["lat"]
    conversation.destination_lon = result["lon"]
    conversation.save()
    return result["lat"], result["lon"], result["display_name"]



def _greet(conversation, entities):
    return {"text": pick("greet")}


def _goodbye(conversation, entities):
    return {"text": pick("goodbye")}


def _thank(conversation, entities):
    return {"text": pick("thank")}


def _affirm(conversation, entities):
    return {"text": pick("affirm")}


def _deny(conversation, entities):
    return {"text": pick("deny")}


def _start_trip_planning(conversation, entities):
    return _continue_trip_planning(conversation)


def _inform_destination(conversation, entities):
    ack = pick("ack_destination", destination=conversation.destination)
    return _continue_trip_planning(conversation, acknowledgment=ack)


def _inform_dates(conversation, entities):
    ack = pick("ack_dates")
    return _continue_trip_planning(conversation, acknowledgment=ack)


def _inform_budget(conversation, entities):
    ack = pick(
        "ack_budget",
        budget=conversation.budget,
        currency=conversation.currency or "",
    ).replace(" .", ".")
    return _continue_trip_planning(conversation, acknowledgment=ack)


def _inform_sustainability_level(conversation, entities):
    ack = pick("ack_sustainability")
    return _continue_trip_planning(conversation, acknowledgment=ack)



def _find_hotels_response(conversation) -> dict:
    coords = _ensure_coordinates(conversation)
    if not coords:
        return {"text": pick("hotels_geocode_fail", destination=conversation.destination)}
    lat, lon, name = coords
    hotels = hotels_service.find_hotels(lat, lon)

    if not hotels:
        return {
            "text": pick("hotels_empty", destination=name),
            "action": "hotel_results",
            "hotels": [],
        }

    any_proxy = any(h["eco_status"] == "eco proxy" for h in hotels)
    text = pick("hotels_intro", destination=name)
    if any_proxy:
        text += " " + ECO_PROXY_DISCLAIMER
    return {
        "text": text,
        "action": "hotel_results",
        "destination": name,
        "hotels": hotels[:10],
    }


def _find_transport_response(conversation) -> dict:
    coords = _ensure_coordinates(conversation)
    if not coords:
        return {"text": pick("transport_geocode_fail", destination=conversation.destination)}
    lat, lon, name = coords
    stops = transport_service.find_transport(lat, lon)
    verdict = transport_service.transport_verdict(stops)
    return {
        "text": pick("transport_intro", destination=name, verdict=verdict),
        "action": "transport_results",
        "destination": name,
        "stops": stops[:12],
        "verdict": verdict,
    }


def _find_attractions_response(conversation) -> dict:
    coords = _ensure_coordinates(conversation)
    if not coords:
        return {"text": pick("attractions_geocode_fail", destination=conversation.destination)}
    lat, lon, name = coords
    sites = attractions_service.find_attractions(lat, lon)

    enriched = []
    links = []
    for site in sites[:6]:
        info = place_description_service.describe(site["name"], sentences=1)
        entry = dict(site)
        if info:
            entry["summary"] = info["summary"]
            entry["url"] = info["url"]
            if info["url"]:
                links.append({"label": f"{site['name']} on Wikipedia", "url": info["url"]})
        enriched.append(entry)

    if not enriched:
        return {
            "text": pick("attractions_empty", destination=name),
            "action": "attraction_results",
            "attractions": [],
        }

    return {
        "text": pick("attractions_intro", destination=name),
        "action": "attraction_results",
        "destination": name,
        "attractions": enriched,
        "links": links,
    }


def _weather_forecast_response(conversation) -> dict:
    coords = _ensure_coordinates(conversation)
    if not coords:
        return {"text": pick("weather_geocode_fail", destination=conversation.destination)}
    lat, lon, name = coords
    weather = weather_service_get(lat, lon)

    if not weather:
        return {"text": pick("weather_unavailable", destination=name)}

    today = weather["daily"][0] if weather["daily"] else None
    summary = (
        f"Right now in {name}: {weather['current']['temperature']}°C. "
        + (f"Today looks {today['advice']}." if today else "")
    )
    return {
        "text": summary,
        "action": "weather_results",
        "destination": name,
        "weather": weather,
    }


def weather_service_get(lat, lon):
    from . import weather as weather_service
    return weather_service.get_weather(lat, lon)


ACTION_RESPONSES: Dict[str, Callable] = {
    "find_hotels": _find_hotels_response,
    "find_transport": _find_transport_response,
    "find_attractions": _find_attractions_response,
    "weather_forecast": _weather_forecast_response,
}

_ask_hotels = _require_slots_then("find_hotels", ACTION_RESPONSES["find_hotels"])
_ask_transport = _require_slots_then("find_transport", ACTION_RESPONSES["find_transport"])
_ask_attractions = _require_slots_then("find_attractions", ACTION_RESPONSES["find_attractions"])
_ask_weather = _require_slots_then("weather_forecast", ACTION_RESPONSES["weather_forecast"])


def _ask_carbon_footprint(conversation, entities):
    """
    Rather than trying to parse "train, then 40km by taxi" out of free
    text, hand the front end a small structured form: one row per leg
    (mode + distance), "add another leg", then Calculate. The form posts
    to /chatbot/api/carbon/ - see views.carbon_api.
    """
    return {
        "text": "Sure — add each leg of your journey below and I'll estimate the total footprint.",
        "action": "carbon_form",
        "vehicle_options": carbon_service.VEHICLE_LABELS,
    }


def _ask_place_description(conversation, entities):
    place = get_entity(entities, "destination") or conversation.destination
    if not place:
        return {"text": "Which place would you like me to describe?"}

    info = place_description_service.describe(place)
    if not info:
        return {"text": f"I couldn't find a Wikipedia article for {place}."}

    links = [{"label": f"{info['title']} on Wikipedia", "url": info["url"]}] if info["url"] else []
    return {
        "text": f"{info['title']}: {info['summary']}",
        "links": links,
    }


def _request_human_handover(conversation, entities):
    conversation.handed_over = True
    conversation.save()
    return {"text": "I'm connecting you with a human travel advisor.", "type": "handover"}



def build_itinerary(conversation) -> dict:
    """
    Once every slot is filled, pull everything together: weather,
    attractions, hotels (with the eco-proxy disclaimer where relevant),
    a transport verdict, a short place description, and the user's
    budget converted to EUR/USD/GBP for quick reference.
    """
    coords = _ensure_coordinates(conversation)
    if not coords:
        return {
            "text": pick("itinerary_geocode_fail", destination=conversation.destination),
            "_skip_intro": True,
        }

    lat, lon, name = coords

    weather = weather_service_get(lat, lon)
    stops = transport_service.find_transport(lat, lon)
    transport_verdict = transport_service.transport_verdict(stops)
    hotels = hotels_service.find_hotels(lat, lon, limit=6)
    sites = attractions_service.find_attractions(lat, lon, limit=5)
    description = place_description_service.describe(conversation.destination, sentences=2)

    budget_conversions = []
    if conversation.budget and conversation.currency:
        for target in ["EUR", "USD", "GBP"]:
            if target == conversation.currency.upper():
                continue
            amount, rate, date = currency_service.convert(
                float(conversation.budget), conversation.currency, target
            )
            if amount is not None:
                budget_conversions.append(
                    {"currency": target, "amount": round(amount, 2), "rate_date": date}
                )

    any_proxy = any(h["eco_status"] == "eco proxy" for h in hotels)

    itinerary = {
        "destination": name,
        "description": description,
        "weather": weather,
        "attractions": sites,
        "hotels": hotels,
        "transport_verdict": transport_verdict,
        "budget_conversions": budget_conversions,
        "eco_disclaimer": ECO_PROXY_DISCLAIMER if any_proxy else None,
    }

    links = []
    if description and description.get("url"):
        links.append({"label": f"{description['title']} on Wikipedia", "url": description["url"]})

    return {
        "text": "",
        "action": "trip_plan",
        "itinerary": itinerary,
        "links": links,
    }


INTENT_HANDLERS: Dict[str, Callable] = {
    "greet": _greet,
    "goodbye": _goodbye,
    "thank": _thank,
    "affirm": _affirm,
    "deny": _deny,
    "start_trip_planning": _start_trip_planning,
    "inform_destination": _inform_destination,
    "inform_dates": _inform_dates,
    "inform_budget": _inform_budget,
    "inform_sustainability_level": _inform_sustainability_level,
    "ask_hotels": _ask_hotels,
    "ask_transport": _ask_transport,
    "ask_attractions": _ask_attractions,
    "ask_weather": _ask_weather,
    "ask_carbon_footprint": _ask_carbon_footprint,
    "ask_place_description": _ask_place_description,
    "request_human_handover": _request_human_handover,
}


SHORT_NO_RE = re.compile(r"^(no|none|nope|nothing|any|anything|whatever)\b", re.IGNORECASE)

NO_PREFERENCE_RE = re.compile(
    r"\bno (particular |specific )?(preference|priorit)"
    r"|\bnone particular\b"
    r"|\b(don'?t|do not) (really )?(mind|care)\b"
    r"|\b(doesn'?t|does not) matter\b"
    r"|\bnot (really |that )?(particular|fussed|bothered|important)\b",
    re.IGNORECASE,
)

SUSTAINABILITY_KEYWORDS = [
    (re.compile(r"low[- ]carbon|low[- ]emission|lowest carbon", re.I), "low-carbon travel"),
    (re.compile(r"eco[- ]?certified|certified|green key|eco[- ]?label", re.I), "eco-certified stays"),
]


def _answer_awaited_slot(conversation, message):
    """
    The bot always asks for the first missing slot. The sustainability
    question is open-ended, and the NLU often misses short answers such as
    "none particular preference" (it returns deny / a low-confidence intent,
    so the plan never completed). When that is the question on the table,
    treat a short reply as the answer. Returns a response dict, or None to
    fall through to normal intent routing.
    """
    missing = missing_slots(conversation)
    if not missing or missing[0] != "sustainability_level" or not message:
        return None

    text = message.strip()
    if not text or len(text.split()) > 10:
        return None

    value = None
    for pattern, label in SUSTAINABILITY_KEYWORDS:
        if pattern.search(text):
            value = label
            break
    if value is None and (
        NO_PREFERENCE_RE.search(text)
        or (len(text.split()) <= 4 and SHORT_NO_RE.search(text))
    ):
        value = "no preference"
    if value is None:
        return None

    conversation.sustainability_level = value
    conversation.fallback_count = 0
    conversation.save()
    return _inform_sustainability_level(conversation, [])


def handle_intent(
    intent: str,
    confidence: float,
    entities: List[dict],
    conversation,
    message: Optional[str] = None,
) -> dict:
   

    apply_entities(conversation, entities)

    direct = _answer_awaited_slot(conversation, message)
    if direct is not None:
        return direct

    if confidence < CONFIDENCE_THRESHOLD:
        conversation.fallback_count += 1
        conversation.save()

        if conversation.fallback_count >= MAX_FALLBACKS_BEFORE_HANDOVER:
            conversation.handed_over = True
            conversation.save()
            return {
                "text": pick("handover"),
                "type": "handover",
            }

        return {
            "text": pick("fallback"),
            "type": "fallback",
        }

    conversation.fallback_count = 0
    conversation.save()

    logger.debug(
        "intent=%s confidence=%.3f entities=%s destination=%s dates=%s "
        "budget=%s currency=%s sustainability=%s",
        intent, confidence, entities, conversation.destination,
        conversation.dates, conversation.budget, conversation.currency,
        conversation.sustainability_level,
    )

    handler = INTENT_HANDLERS.get(intent)
    if handler:
        return handler(conversation, entities)

    missing = missing_slots(conversation)
    if missing:
        return {
            "text": "Sorry, I didn't catch that. " + pick_slot_question(missing[0]),
            "awaiting_slot": missing[0],
            "intent": intent,
            "confidence": confidence,
        }
    return {
        "text": (
            "I understood your message, but I'm not sure what "
            "you'd like me to do next."
        ),
        "intent": intent,
        "confidence": confidence,
    }
