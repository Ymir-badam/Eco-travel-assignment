from django.contrib import admin

from .models import CarbonCalculation, Conversation, ExchangeRate, Message, UserConsent, VehicleLeg


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):

    list_display = (
        "session_id",
        "user",
        "destination",
        "dates",
        "budget",
        "currency",
        "sustainability_level",
        "fallback_count",
        "handed_over",
        "updated_at",
    )

    search_fields = (
        "session_id",
        "destination",
        "user__username",
    )

    list_filter = (
        "handed_over",
        "sustainability_level",
    )


class VehicleLegInline(admin.TabularInline):
    model = VehicleLeg
    extra = 0


@admin.register(CarbonCalculation)
class CarbonCalculationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "conversation", "total_emission_kg", "best_mode", "created_at")
    inlines = [VehicleLegInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "text", "created_at")
    list_filter = ("sender",)
    search_fields = ("text",)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency_code", "rate_per_eur", "rate_date", "updated_at")
    search_fields = ("currency_code",)


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "policy_version", "accepted_at")
