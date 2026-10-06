import uuid

from .models import Conversation
from .nlu import RasaNLU
from .services.router_service import handle_intent

ACTIVE_CONVERSATION_SESSION_KEY = "active_conversation_id"


def _get_by_id_for_owner(request, conversation_id):
 
    try:
        conversation = Conversation.objects.get(pk=conversation_id)
    except Conversation.DoesNotExist:
        return None

    if request.user.is_authenticated:
        if conversation.user_id == request.user.id:
            return conversation
        return None

    if conversation.session_id == request.session.session_key:
        return conversation

    return None


def get_conversation(request, conversation_id=None):
    

    if not request.session.session_key:
        request.session.create()

    if conversation_id is not None:
        conversation = _get_by_id_for_owner(request, conversation_id)
        if conversation:
            request.session[ACTIVE_CONVERSATION_SESSION_KEY] = conversation.pk
            return conversation

    active_id = request.session.get(ACTIVE_CONVERSATION_SESSION_KEY)
    if active_id is not None:
        conversation = _get_by_id_for_owner(request, active_id)
        if conversation:
            return conversation

    if request.user.is_authenticated:
        conversation = (
            Conversation.objects.filter(user=request.user)
            .order_by("-updated_at")
            .first()
        )
        if conversation:
            request.session[ACTIVE_CONVERSATION_SESSION_KEY] = conversation.pk
            return conversation
        return start_new_conversation(request)

    session_id = request.session.session_key
    conversation, _created = Conversation.objects.get_or_create(session_id=session_id)
    request.session[ACTIVE_CONVERSATION_SESSION_KEY] = conversation.pk
    return conversation


def start_new_conversation(request):
    
    conversation = Conversation.objects.create(
        session_id=str(uuid.uuid4()),
        user=request.user if request.user.is_authenticated else None,
    )
    request.session[ACTIVE_CONVERSATION_SESSION_KEY] = conversation.pk
    return conversation


def route_nlu_result(
    nlu_result,
    conversation,
):
    """
    Convert the Rasa NLU result into a Django
    conversation action.
    """

    intent_data = (
        nlu_result.get("intent")
        or {}
    )

    intent = intent_data.get(
        "name",
        "",
    )

    confidence = float(
        intent_data.get(
            "confidence",
            0,
        )
        or 0
    )

    entities = (
        nlu_result.get("entities")
        or []
    )

    return handle_intent(
        intent=intent,
        confidence=confidence,
        entities=entities,
        conversation=conversation,
        message=nlu_result.get("text"),
    )


def process_message(request, message, conversation=None):
   

    if conversation is None:
        conversation = get_conversation(request)

    nlu_result = RasaNLU.parse(message)

    result = route_nlu_result(
        nlu_result=nlu_result,
        conversation=conversation,
    )

    conversation.save()

    if isinstance(result, dict):
        response = result
    else:
        response = {
            "response": str(result),
        }

    response.setdefault(
        "intent",
        nlu_result.get(
            "intent",
            {},
        ),
    )

    response.setdefault(
        "entities",
        nlu_result.get(
            "entities",
            [],
        ),
    )

    return response
