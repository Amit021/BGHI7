from django.test import TestCase

from base.forms import MyUserCreationForm
from base.models import InvitationCode, User


class MyUserCreationFormTests(TestCase):
    def test_student_email_does_not_require_invitation_code(self):
        form = MyUserCreationForm(
            data={
                "name": "Student",
                "username": "student1",
                "email": "student1@th-deg.de",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.affiliation, User.Affiliation.STUDENT)

    def test_alumni_email_requires_valid_invitation_code(self):
        InvitationCode.objects.create(code="INVITE123")

        form = MyUserCreationForm(
            data={
                "name": "Alumni",
                "username": "alumni1",
                "email": "alumni1@gmail.com",
                "invitation_code": "INVITE123",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.affiliation, User.Affiliation.ALUMNI)

        invite = InvitationCode.objects.get(code="INVITE123")
        self.assertIsNotNone(invite.used_at)
        self.assertEqual(invite.used_by_id, user.id)

    def test_alumni_email_missing_invitation_code_is_invalid(self):
        form = MyUserCreationForm(
            data={
                "name": "Alumni",
                "username": "alumni2",
                "email": "alumni2@gmail.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("invitation_code", form.errors)

    def test_alumni_email_invalid_invitation_code_is_invalid(self):
        form = MyUserCreationForm(
            data={
                "name": "Alumni",
                "username": "alumni3",
                "email": "alumni3@gmail.com",
                "invitation_code": "NOPE",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("invitation_code", form.errors)
