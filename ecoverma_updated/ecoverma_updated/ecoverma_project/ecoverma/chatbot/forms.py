from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = None  

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django import forms

        self.fields["email"] = forms.EmailField(required=False)
        self.fields["consent"] = forms.BooleanField(
            required=True,
            label="I agree to the privacy notice",
            error_messages={"required": "You must agree to the privacy notice to create an account."},
            widget=forms.CheckboxInput(attrs={"class": "consent-checkbox"}),
        )
        self.order_fields(["username", "email", "password1", "password2", "consent"])

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-input")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
        return user
