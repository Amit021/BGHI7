from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings
from .models import Room, User, MentorProfile
from .models import InvitationCode


def is_student_email(email):
    """Check if email belongs to a university student domain."""
    email = (email or '').strip().lower()
    # Support list of domains (new) or single domain (legacy)
    domains = getattr(settings, 'UNIVERSITY_EMAIL_DOMAINS', None)
    if not domains:
        # Fallback to single domain setting
        domain = getattr(settings, 'UNIVERSITY_EMAIL_DOMAIN', '')
        domains = [domain] if domain else []
    
    for domain in domains:
        domain = domain.strip().lower()
        if domain and email.endswith(f"@{domain}"):
            return True
    return False


class MyUserCreationForm(UserCreationForm):
    invitation_code = forms.CharField(
        required=False,
        max_length=64,
        help_text='Required for alumni (non-university email).',
    )

    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'invitation_code', 'password1', 'password2']

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        return email

    def clean(self):
        cleaned_data = super().clean()

        email = (cleaned_data.get('email') or '').strip().lower()
        if not email:
            return cleaned_data

        if is_student_email(email):
            return cleaned_data

        code = (cleaned_data.get('invitation_code') or '').strip()
        if not code:
            self.add_error('invitation_code', 'Alumni registration requires an invitation code.')
            return cleaned_data

        invite = InvitationCode.objects.filter(code=code, is_active=True, used_at__isnull=True).first()
        if not invite:
            self.add_error('invitation_code', 'Invalid or already used invitation code.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = (user.username or '').lower()
        user.email = (user.email or '').lower()

        invite = None
        code = (self.cleaned_data.get('invitation_code') or '').strip()
        if not is_student_email(user.email):
            invite = InvitationCode.objects.filter(code=code, is_active=True, used_at__isnull=True).first()
            user.affiliation = User.Affiliation.ALUMNI
        else:
            user.affiliation = User.Affiliation.STUDENT

        if commit:
            user.save()
            if invite is not None:
                from django.utils import timezone

                invite.used_by = user
                invite.used_at = timezone.now()
                invite.save(update_fields=['used_by', 'used_at'])
        return user

class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        exclude = ['host', 'participants']

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['avatar', 'name', 'username', 'email', 'bio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bio should be optional
        self.fields['bio'].required = False

        # Avatar should be optional too (usually)
        self.fields['avatar'].required = False


class MentorProfileForm(ModelForm):
    class Meta:
        model = MentorProfile
        fields = ['is_available_as_mentor', 'is_seeking_mentor', 'mentor_topics', 'seeking_topics', 'experience']
        widgets = {
            'mentor_topics': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., Python, Machine Learning, Career Advice'}),
            'seeking_topics': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., Data Science, Interview Prep'}),
            'experience': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Brief description of your background and expertise'}),
        }
        labels = {
            'is_available_as_mentor': 'I am available as a mentor',
            'is_seeking_mentor': 'I am looking for a mentor',
            'mentor_topics': 'Topics I can mentor on (comma separated)',
            'seeking_topics': 'Topics I want to learn about (comma separated)',
            'experience': 'My experience/background',
        }