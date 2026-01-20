from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    class Affiliation(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        ALUMNI = 'ALUMNI', 'Alumni'

    name = models.CharField(max_length=200, null=True)
    email = models.EmailField(unique=True, null=True)
    bio = models.TextField(null=True)
    avatar = models.ImageField(null=True, default="avatar.svg")
    affiliation = models.CharField(
        max_length=20,
        choices=Affiliation.choices,
        default=Affiliation.STUDENT,
    )
    # Demo paid flag (no real payments). Used to gate premium-only categories.
    is_paid = models.BooleanField(default=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


class InvitationCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_invite_codes',
    )
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='used_invite_code',
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

class Topic(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

class Room(models.Model):
    host = models.ForeignKey(User, on_delete = models.SET_NULL, null = True)
    topic = models.ForeignKey(Topic, on_delete = models.SET_NULL, null = True)
    name = models.TextField()
    description = models.TextField(null= True, blank= True)
    # File attachment (for Study Materials category)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)
    participants = models.ManyToManyField(User, related_name='participants', blank= True)
    updated = models.DateTimeField(auto_now= True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.name
    
    def get_attachment_filename(self):
        """Return just the filename from the attachment path."""
        if self.attachment:
            import os
            return os.path.basename(self.attachment.name)
        return None
    
    def is_study_material(self):
        """Check if this post belongs to Study Materials category."""
        if self.topic:
            return self.topic.slug in ['exams-study', 'tech-projects']
        return False


class PostVote(models.Model):
    class Value(models.IntegerChoices):
        DOWN = -1, 'Downvote'
        UP = 1, 'Upvote'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='votes')
    value = models.IntegerField(choices=Value.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'room'], name='unique_post_vote'),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.room_id}:{self.value}"
    

class Message(models.Model):
    user = models.ForeignKey(User, on_delete= models.CASCADE)
    room = models.ForeignKey(Room, on_delete = models.CASCADE)
    body = models.TextField()
    # File attachment for Study Materials comments
    attachment = models.FileField(upload_to='comment_attachments/', null=True, blank=True)
    updated = models.DateTimeField(auto_now= True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.body[0:50]
    
    def get_attachment_filename(self):
        """Return just the filename from the attachment path."""
        if self.attachment:
            import os
            return os.path.basename(self.attachment.name)
        return None


class DirectMessage(models.Model):
    """Private messages between users."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.content[:30]}"


class MentorProfile(models.Model):
    """Tracks user's mentorship availability and interests."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    is_available_as_mentor = models.BooleanField(default=False)
    is_seeking_mentor = models.BooleanField(default=False)
    mentor_topics = models.TextField(blank=True, help_text="Topics you can mentor on (comma separated)")
    seeking_topics = models.TextField(blank=True, help_text="Topics you want to learn about (comma separated)")
    experience = models.TextField(blank=True, help_text="Brief description of your experience")
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = []
        if self.is_available_as_mentor:
            status.append("Mentor")
        if self.is_seeking_mentor:
            status.append("Mentee")
        return f"{self.user.username} - {', '.join(status) if status else 'Inactive'}"

    def get_mentor_topics_list(self):
        """Return mentor topics as a list."""
        if self.mentor_topics:
            return [t.strip() for t in self.mentor_topics.split(',') if t.strip()]
        return []

    def get_seeking_topics_list(self):
        """Return seeking topics as a list."""
        if self.seeking_topics:
            return [t.strip() for t in self.seeking_topics.split(',') if t.strip()]
        return []