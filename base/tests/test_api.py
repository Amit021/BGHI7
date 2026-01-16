from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from base.models import Room, Topic, User


class ApiTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
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

    def test_api_requires_auth(self):
        resp = self.client_api.get(reverse("api-routes"))
        self.assertIn(resp.status_code, (401, 403))

    def test_unpaid_user_cannot_access_jobs_referrals(self):
        self.user.is_paid = False
        self.user.save(update_fields=["is_paid"])
        self.client_api.force_authenticate(user=self.user)

        rooms_resp = self.client_api.get(reverse("api-rooms"))
        self.assertEqual(rooms_resp.status_code, 200)
        ids = {room["id"] for room in rooms_resp.json()}
        self.assertIn(self.general_room.id, ids)
        self.assertNotIn(self.jobs_room.id, ids)

        job_room_resp = self.client_api.get(reverse("api-room", kwargs={"pk": self.jobs_room.id}))
        self.assertEqual(job_room_resp.status_code, 403)

    def test_paid_user_can_access_jobs_referrals(self):
        self.user.is_paid = True
        self.user.save(update_fields=["is_paid"])
        self.client_api.force_authenticate(user=self.user)

        rooms_resp = self.client_api.get(reverse("api-rooms"))
        self.assertEqual(rooms_resp.status_code, 200)
        ids = {room["id"] for room in rooms_resp.json()}
        self.assertIn(self.general_room.id, ids)
        self.assertIn(self.jobs_room.id, ids)

        job_room_resp = self.client_api.get(reverse("api-room", kwargs={"pk": self.jobs_room.id}))
        self.assertEqual(job_room_resp.status_code, 200)
        self.assertEqual(job_room_resp.json()["id"], self.jobs_room.id)
