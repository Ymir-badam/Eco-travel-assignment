from django.conf import settings
from django.db import models


class Conversation(models.Model):
    

    session_id = models.CharField(
        max_length=100,
        unique=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )

    destination = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    dates = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    currency = models.CharField(
        max_length=10,
        blank=True,
        null=True,
    )

    sustainability_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    destination_lat = models.FloatField(
        blank=True,
        null=True,
    )

    destination_lon = models.FloatField(
        blank=True,
        null=True,
    )

    extra_entities = models.JSONField(
        default=dict,
        blank=True,
    )

    pending_action = models.CharField(
        max_length=64,
        blank=True,
        null=True,
    )

    fallback_count = models.IntegerField(
        default=0,
    )

    handed_over = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.session_id

    @property
    def title(self):
        """Short label for the conversation-history sidebar."""
        if self.destination:
            return f"Trip to {self.destination}"
        first_user_message = self.messages.filter(sender="user").first()
        if first_user_message and first_user_message.text:
            text = first_user_message.text.strip()
            return text if len(text) <= 40 else text[:37] + "..."
        return "New conversation"

    @property
    def preview(self):
        """Last message's text, trimmed, for the sidebar subtitle."""
        last_message = self.messages.last()
        if not last_message or not last_message.text:
            return "No messages yet"
        text = last_message.text.strip()
        return text if len(text) <= 60 else text[:57] + "..."


class Message(models.Model):
   

    SENDER_USER = "user"
    SENDER_BOT = "bot"
    SENDER_CHOICES = [
        (SENDER_USER, "User"),
        (SENDER_BOT, "Bot"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
    )

    text = models.TextField(
        blank=True,
    )

    links = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        preview = (self.text or "")[:40]
        return f"{self.sender}: {preview}"

    @property
    def day(self):
        return self.created_at.date()

    @property
    def time(self):
        return self.created_at.time()


class CarbonCalculation(models.Model):
    

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="carbon_calculations",
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carbon_calculations",
    )

    total_emission_kg = models.FloatField(
        default=0,
    )

    best_mode = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Carbon calc #{self.pk} - {self.total_emission_kg} kg CO2e"


class VehicleLeg(models.Model):
    

    VEHICLE_CHOICES = [
        ("walk", "Walking"),
        ("cycle", "Cycling"),
        ("train", "Train"),
        ("coach", "Coach / long-distance bus"),
        ("electric_car", "Electric car"),
        ("car_petrol", "Petrol car"),
        ("ferry", "Ferry"),
        ("flight_short", "Short-haul flight"),
        ("flight_long", "Long-haul flight"),
    ]

    calculation = models.ForeignKey(
        CarbonCalculation,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_CHOICES,
    )

    distance_km = models.FloatField()

    emission_kg = models.FloatField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.get_vehicle_type_display()} - {self.distance_km} km"


class ExchangeRate(models.Model):
    
    currency_code = models.CharField(
        max_length=10,
        unique=True,
    )

    rate_per_eur = models.DecimalField(
        max_digits=20,
        decimal_places=8,
    )

    
    rate_date = models.DateField()

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["currency_code"]

    def __str__(self):
        return f"1 EUR = {self.rate_per_eur} {self.currency_code} ({self.rate_date})"


class UserConsent(models.Model):
    

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consents",
    )

    policy_version = models.CharField(max_length=20)

    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "policy_version")]
        ordering = ["-accepted_at"]

    def __str__(self):
        return f"{self.user_id} accepted v{self.policy_version} on {self.accepted_at:%Y-%m-%d}"
