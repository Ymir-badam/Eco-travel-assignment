
import asyncio
import threading

from django.conf import settings


class RasaNLU:

    _agent = None
    _lock = threading.Lock()

    @classmethod
    def load_model(cls):

        if cls._agent is not None:
            return cls._agent

        with cls._lock:

            if cls._agent is not None:
                return cls._agent

            from rasa.core.agent import Agent

            model_path = settings.RASA_NLU_MODEL

            print(
                f"Loading Rasa NLU model from: {model_path}"
            )

            cls._agent = Agent.load(
                model_path=model_path
            )

            print("Rasa NLU model loaded successfully.")

            return cls._agent

    @classmethod
    def parse(cls, text):

        agent = cls.load_model()

        text = text.strip()

        if not text:
            return {
                "text": text,
                "intent": {
                    "name": "",
                    "confidence": 0.0,
                },
                "entities": [],
            }

        result = asyncio.run(
            agent.parse_message(
                message_data=text
            )
        )

        return result

    @classmethod
    def reset(cls):

        with cls._lock:
            cls._agent = None

