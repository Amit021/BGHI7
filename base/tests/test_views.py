from django.test import TestCase
from django.urls import reverse

from base.models import Message, PostVote, Room, Topic, User


class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user1@th-deg.de",
            password="pass12345",
        )
        self.jobs_topic, _ = Topic.objects.get_or_create(
            slug="jobs-referrals",
            defaults={"name": "Jobs & Referrals"},
        )
        self.general_topic, _ = Topic.objects.get_or_create(
            slug="general",
            defaults={"name": "General"},
        )

        self.jobs_room = Room.objects.create(
            host=self.user,
            topic=self.jobs_topic,
            name="Jobs Room",
            description="Jobs",
        )
        self.general_room = Room.objects.create(
            host=self.user,
            topic=self.general_topic,
            name="General Room",
            description="General",
        )

    def login(self, user=None):
        user = user or self.user
        ok = self.client.login(email=user.email, password="pass12345")
        self.assertTrue(ok)

    def test_home_requires_login(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_home_excludes_jobs_referrals_for_unpaid(self):
        self.login()
        self.user.is_paid = False
        self.user.save(update_fields=["is_paid"])

        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        rooms = list(resp.context["rooms"])
        self.assertIn(self.general_room, rooms)
        self.assertNotIn(self.jobs_room, rooms)

    def test_selecting_jobs_referrals_topic_redirects_unpaid(self):
        self.login()
        self.user.is_paid = False
        self.user.save(update_fields=["is_paid"])

        resp = self.client.get(reverse("home"), {"topic": "jobs-referrals"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("home"))

    def test_paid_user_can_view_jobs_referrals_room(self):
        self.login()
        self.user.is_paid = True
        self.user.save(update_fields=["is_paid"])

        resp = self.client.get(reverse("room", kwargs={"pk": self.jobs_room.id}))
        self.assertEqual(resp.status_code, 200)

    def test_unpaid_user_cannot_view_jobs_referrals_room(self):
        self.login()
        self.user.is_paid = False
        self.user.save(update_fields=["is_paid"])

        resp = self.client.get(reverse("room", kwargs={"pk": self.jobs_room.id}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("home"))

    def test_post_message_adds_participant(self):
        self.login()

        resp = self.client.post(
            reverse("room", kwargs={"pk": self.general_room.id}),
            data={"body": "hello"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Message.objects.filter(room=self.general_room, user=self.user, body="hello").exists()
        )
        self.assertTrue(self.general_room.participants.filter(id=self.user.id).exists())

    def test_vote_toggles_same_direction(self):
        self.login()

        vote_url = reverse("vote-room", kwargs={"pk": self.general_room.id})

        resp = self.client.post(vote_url, data={"direction": "up"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(PostVote.objects.filter(user=self.user, room=self.general_room, value=1).exists())

        # Same vote again removes
        resp = self.client.post(vote_url, data={"direction": "up"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(PostVote.objects.filter(user=self.user, room=self.general_room).exists())

    def test_vote_switches_direction(self):
        self.login()

        vote_url = reverse("vote-room", kwargs={"pk": self.general_room.id})
        self.client.post(vote_url, data={"direction": "up"})
        self.assertTrue(PostVote.objects.filter(user=self.user, room=self.general_room, value=1).exists())

        self.client.post(vote_url, data={"direction": "down"})
        self.assertTrue(PostVote.objects.filter(user=self.user, room=self.general_room, value=-1).exists())

    def test_demo_subscribe_unsubscribe(self):
        self.login()

        self.user.is_paid = False
        self.user.save(update_fields=["is_paid"])

        resp = self.client.post(reverse("demo-subscribe"))
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_paid)

        resp = self.client.post(reverse("demo-unsubscribe"))
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_paid)
