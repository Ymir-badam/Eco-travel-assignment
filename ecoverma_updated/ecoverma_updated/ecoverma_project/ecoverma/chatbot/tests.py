from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .consent import has_consent, record_consent
from .models import CarbonCalculation, Conversation, Message
from .services import retention


class RetentionTests(TestCase):
    def _conversation(self, session_id, age_days):
        conv = Conversation.objects.create(session_id=session_id)
        Message.objects.create(conversation=conv, sender="user", text="hi")
        Conversation.objects.filter(pk=conv.pk).update(
            created_at=timezone.now() - timedelta(days=age_days)
        )
        return conv

    def test_old_conversations_are_deleted_new_ones_kept(self):
        old = self._conversation("old", 8)
        new = self._conversation("new", 6)
        CarbonCalculation.objects.create(conversation=new)

        result = retention.purge_expired()

        self.assertEqual(result["conversations"], 1)
        self.assertFalse(Conversation.objects.filter(pk=old.pk).exists())
        self.assertTrue(Conversation.objects.filter(pk=new.pk).exists())
        self.assertEqual(Message.objects.filter(conversation=old).count(), 0)
        self.assertEqual(Message.objects.filter(conversation=new).count(), 1)
        self.assertEqual(CarbonCalculation.objects.count(), 1)


class ConsentTests(TestCase):
    def test_signup_requires_consent_and_records_it(self):
        data = {"username": "ana", "password1": "S3cure-pass-xyz", "password2": "S3cure-pass-xyz"}
        response = self.client.post(reverse("chatbot:signup"), data)
        self.assertEqual(response.status_code, 200)  # form re-shown with error
        self.assertFalse(User.objects.filter(username="ana").exists())

        response = self.client.post(reverse("chatbot:signup"), {**data, "consent": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(has_consent(User.objects.get(username="ana")))

    def test_existing_user_without_consent_is_redirected(self):
        User.objects.create_user("bob", password="pw12345!")
        self.client.login(username="bob", password="pw12345!")
        response = self.client.get(reverse("chatbot:chat"))
        self.assertRedirects(response, reverse("chatbot:consent"), fetch_redirect_response=False)

        self.client.post(reverse("chatbot:consent"), {"consent": "on"})
        self.assertEqual(self.client.get(reverse("chatbot:chat")).status_code, 200)

    def test_delete_account_removes_everything(self):
        user = User.objects.create_user("cy", password="pw12345!")
        record_consent(user)
        Conversation.objects.create(session_id="s1", user=user)
        self.client.login(username="cy", password="pw12345!")
        self.client.post(reverse("chatbot:delete_account"))
        self.assertFalse(User.objects.filter(username="cy").exists())
        self.assertEqual(Conversation.objects.count(), 0)
