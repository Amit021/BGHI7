from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from .models import Room, Topic, Message, User, PostVote, DirectMessage, MentorProfile
from .forms import RoomForm, UserForm, MyUserCreationForm, MentorProfileForm


JOBS_REFERRALS_SLUG = 'jobs-referrals'
STUDY_MATERIALS_SLUGS = ['exams-study', 'tech-projects']

# Category groupings for landing page
CATEGORY_GROUPS = {
    'community': ['wellbeing', 'events-clubs', 'housing', 'relocation', 'buy-sell', 'admin-paperwork', 'other'],
    'jobs': ['jobs-referrals', 'internships'],
    'study': ['exams-study', 'tech-projects'],
    'mentorship': ['alumni-network', 'mentorship'],
}


def _user_can_access_jobs_referrals(user):
    return bool(getattr(user, 'is_paid', False))


def _restrict_jobs_referrals_rooms(queryset, user):
    if _user_can_access_jobs_referrals(user):
        return queryset
    return queryset.exclude(topic__slug=JOBS_REFERRALS_SLUG)


def _restrict_jobs_referrals_topics(queryset, user):
    if _user_can_access_jobs_referrals(user):
        return queryset
    return queryset.exclude(slug=JOBS_REFERRALS_SLUG)



def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except:
            messages.error(request, 'User does not exist')
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('landing')
        else:
            messages.error(request, 'Email or password does not exist')
            
    context = {'page': page}
    return render(request, 'base/login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('login')

def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occured during registration') 

    university_domains = getattr(settings, 'UNIVERSITY_EMAIL_DOMAINS', None)
    if not university_domains:
        # Fallback to single domain
        domain = getattr(settings, 'UNIVERSITY_EMAIL_DOMAIN', 'youruni.edu')
        university_domains = [domain] if domain else []
    return render(request, 'base/login_register.html', {'form': form, 'university_domains': university_domains})


def landing(request):
    """Landing page with 4 main categories."""
    # Count posts for each category group
    community_count = Room.objects.filter(topic__slug__in=CATEGORY_GROUPS['community']).count()
    jobs_count = Room.objects.filter(topic__slug__in=CATEGORY_GROUPS['jobs']).count()
    study_count = Room.objects.filter(topic__slug__in=CATEGORY_GROUPS['study']).count()
    mentorship_count = Room.objects.filter(topic__slug__in=CATEGORY_GROUPS['mentorship']).count()

    context = {
        'community_count': community_count,
        'jobs_count': jobs_count,
        'study_count': study_count,
        'mentorship_count': mentorship_count,
    }
    return render(request, 'base/landing.html', context)


@login_required(login_url='login')
def home(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''
    topic_slug = request.GET.get('topic') if request.GET.get('topic') is not None else ''
    category = request.GET.get('category') if request.GET.get('category') is not None else ''

    if topic_slug == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
        messages.error(request, 'Jobs & Referrals is a premium category. Enable premium access to view it.')
        return redirect('home')

    rooms = Room.objects.all()
    
    # Filter by category group (from landing page)
    if category and category in CATEGORY_GROUPS:
        category_slugs = CATEGORY_GROUPS[category]
        rooms = rooms.filter(topic__slug__in=category_slugs)
    
    if topic_slug:
        rooms = rooms.filter(topic__slug=topic_slug)
    if q:
        rooms = rooms.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(topic__name__icontains=q)
        )

    rooms = _restrict_jobs_referrals_rooms(rooms, request.user)
    rooms = rooms.annotate(score=Coalesce(Sum('votes__value'), 0)).order_by('-created')

    topics = _restrict_jobs_referrals_topics(Topic.objects.all(), request.user)
    room_count = rooms.count()
    room_messages = Message.objects.filter(Q(room__topic__slug=topic_slug) if topic_slug else Q())
    if not _user_can_access_jobs_referrals(request.user):
        room_messages = room_messages.exclude(room__topic__slug=JOBS_REFERRALS_SLUG)
    if q:
        room_messages = room_messages.filter(Q(room__topic__name__icontains=q) | Q(body__icontains=q))

    # Get category name for display
    category_names = {
        'community': 'Community',
        'jobs': 'Jobs & Careers',
        'study': 'Study Materials',
        'mentorship': 'Mentorship',
    }
    current_category = category_names.get(category, '')

    context = {
        'rooms': rooms, 
        'topics': topics, 
        'room_count': room_count, 
        'room_messages': room_messages,
        'current_category': current_category,
        'is_mentorship_category': category == 'mentorship',
        'is_study_category': category == 'study',
    }
    
    # Add mentorship data if on mentorship category
    if category == 'mentorship':
        mentorship_data = get_mentorship_data()
        context.update(mentorship_data)
        # Check if current user has a mentor profile
        try:
            context['user_mentor_profile'] = request.user.mentor_profile
        except MentorProfile.DoesNotExist:
            context['user_mentor_profile'] = None
    
    return render(request, 'base/home.html', context)


@login_required(login_url='login')
def room(request, pk):
    room = Room.objects.get(id=pk)

    if getattr(room.topic, 'slug', None) == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
        messages.error(request, 'Jobs & Referrals is a premium category. Enable premium access to view and comment.')
        return redirect('home')

    score = room.votes.aggregate(score=Coalesce(Sum('value'), 0))['score']
    room_messages = room.message_set.all().order_by('-created')
    participants = room.participants.all()
    if request.method == 'POST':
        if getattr(room.topic, 'slug', None) == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
            messages.error(request, 'Premium access is required to comment in Jobs & Referrals.')
            return redirect('home')
        
        # Handle file attachment for Study Materials comments
        attachment_file = None
        if room.is_study_material() and 'attachment' in request.FILES:
            uploaded_file = request.FILES['attachment']
            # Validate file type
            allowed_types = ['application/pdf', 'application/msword', 
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if uploaded_file.content_type not in allowed_types:
                messages.error(request, 'Only PDF and Word documents are allowed.')
                return redirect('room', pk=room.id)
            # Validate file size (max 10MB)
            if uploaded_file.size > 10 * 1024 * 1024:
                messages.error(request, 'File size must be less than 10MB.')
                return redirect('room', pk=room.id)
            attachment_file = uploaded_file
        
        message = Message.objects.create(
            user = request.user,
            room = room,
            body = request.POST.get('body'),
            attachment = attachment_file
        )
        room.participants.add(request.user)
        return redirect('room', pk = room.id)

    user_vote = 0
    if request.user.is_authenticated:
        existing = PostVote.objects.filter(user=request.user, room=room).first()
        user_vote = existing.value if existing else 0

    context = {
        'room': room,
        'room_messages': room_messages,
        'participants': participants,
        'score': score,
        'user_vote': user_vote,
    }
    return render (request, 'base/room.html', context)

@login_required(login_url='login')
def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = _restrict_jobs_referrals_rooms(user.room_set.all(), request.user)
    rooms = rooms.annotate(score=Coalesce(Sum('votes__value'), 0)).order_by('-created')
    room_messages = user.message_set.all()
    if not _user_can_access_jobs_referrals(request.user):
        room_messages = room_messages.exclude(room__topic__slug=JOBS_REFERRALS_SLUG)
    topics = _restrict_jobs_referrals_topics(Topic.objects.all(), request.user)
    
    # Get mentor profile if exists
    try:
        mentor_profile = user.mentor_profile
    except MentorProfile.DoesNotExist:
        mentor_profile = None
    
    context = {
        'user': user, 
        'rooms': rooms, 
        'room_messages': room_messages, 
        'topics': topics,
        'mentor_profile': mentor_profile,
    }
    return render(request, 'base/profile.html', context)


@login_required(login_url= 'login')
def createRoom(request):
    form = RoomForm()
    topics = _restrict_jobs_referrals_topics(Topic.objects.all(), request.user)
    # Check if we're creating a study material post
    category = request.GET.get('category', '')
    is_study_category = category == 'study'
    
    # Get default topic based on category
    if is_study_category:
        default_topic = Topic.objects.filter(slug='exams-study').first()
    else:
        default_topic = Topic.objects.filter(slug='community').first()
    if not default_topic:
        default_topic = Topic.objects.first()
    
    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        if not description:
            messages.error(request, 'Please write something.')
            return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': None, 'is_study_category': is_study_category})

        # Generate title from description (first 50 chars)
        name = description[:50] + ('...' if len(description) > 50 else '')

        # Handle file upload for Study Materials
        attachment = None
        if is_study_category and 'attachment' in request.FILES:
            uploaded_file = request.FILES['attachment']
            # Validate file type (PDF and Word documents only)
            allowed_types = ['application/pdf', 'application/msword', 
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if uploaded_file.content_type not in allowed_types:
                messages.error(request, 'Only PDF and Word documents are allowed.')
                return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': None, 'is_study_category': is_study_category})
            # Limit file size to 10MB
            if uploaded_file.size > 10 * 1024 * 1024:
                messages.error(request, 'File size must be less than 10MB.')
                return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': None, 'is_study_category': is_study_category})
            attachment = uploaded_file

        room = Room.objects.create(
            host = request.user,
            topic = default_topic,
            name = name,
            description = description,
            attachment = attachment,
        )

        if is_study_category:
            return redirect('/home/?category=study')
        return redirect('home')

    context = {'form': form, 'topics': topics, 'is_study_category': is_study_category}
    return render(request, 'base/room_form.html', context)

@login_required(login_url= 'login')
def updateRoom(request, pk):
    room = Room.objects.get(id = pk)
    form = RoomForm(instance=room)
    topics = _restrict_jobs_referrals_topics(Topic.objects.all(), request.user)
    if request.user != room.host:
        return HttpResponse('You are not allowed here!')

    if request.method == 'POST':
        topic_id = request.POST.get('topic')
        topic = Topic.objects.filter(id=topic_id).first()
        if not topic:
            messages.error(request, 'Please select a valid category.')
            return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': room})

        if topic.slug == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
            messages.error(request, 'Premium access is required to post in Jobs & Referrals.')
            return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': room})
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')
        
    context = {'form': form, 'topics': topics, 'room': room}
    return render(request, 'base/room_form.html', context)

@login_required(login_url= 'login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj':room})


@login_required(login_url= 'login')
@login_required(login_url='login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('You are not allowed here!')

    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj':message})


@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    # Topics for the left sidebar
    topics = _restrict_jobs_referrals_topics(Topic.objects.all(), request.user)

    # Activity for the right sidebar
    room_messages = Message.objects.all().order_by('-created')
    if not _user_can_access_jobs_referrals(request.user):
        room_messages = room_messages.exclude(room__topic__slug=JOBS_REFERRALS_SLUG)

    context = {
        'form': form,
        'topics': topics,
        'room_messages': room_messages,
    }
    return render(request, 'base/update-user.html', context)


@login_required(login_url='login')
def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Topic.objects.filter(name__icontains=q)
    topics = _restrict_jobs_referrals_topics(topics, request.user)
    return render(request, 'base/topics.html', {'topics': topics})


@login_required(login_url='login')
def voteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if getattr(room.topic, 'slug', None) == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
        messages.error(request, 'Premium access is required for Jobs & Referrals.')
        return redirect('home')

    direction = request.POST.get('direction')
    value = 1 if direction == 'up' else -1

    existing = PostVote.objects.filter(user=request.user, room=room).first()
    if existing and existing.value == value:
        existing.delete()
    else:
        PostVote.objects.update_or_create(
            user=request.user,
            room=room,
            defaults={'value': value},
        )
    return redirect('room', pk=room.id)

@login_required(login_url='login')
def activityPage(request):
    room_messages = Message.objects.all()
    if not _user_can_access_jobs_referrals(request.user):
        room_messages = room_messages.exclude(room__topic__slug=JOBS_REFERRALS_SLUG)
    return render(request, 'base/activity.html', {'room_messages': room_messages})


@login_required(login_url='login')
def demoSubscribe(request):
    if request.method != 'POST':
        return redirect('user-profile', pk=request.user.id)
    request.user.is_paid = True
    request.user.save(update_fields=['is_paid'])
    messages.success(request, 'Premium access enabled. You can now access Jobs & Referrals.')
    return redirect('user-profile', pk=request.user.id)


@login_required(login_url='login')
def demoUnsubscribe(request):
    if request.method != 'POST':
        return redirect('user-profile', pk=request.user.id)
    request.user.is_paid = False
    request.user.save(update_fields=['is_paid'])
    messages.success(request, 'Premium access disabled.')
    return redirect('user-profile', pk=request.user.id)


# ============== MESSAGING VIEWS ==============

@login_required(login_url='login')
def inbox(request):
    """Show list of conversations for the current user."""
    user = request.user
    
    # Get all users the current user has exchanged messages with
    sent_to = DirectMessage.objects.filter(sender=user).values_list('receiver', flat=True)
    received_from = DirectMessage.objects.filter(receiver=user).values_list('sender', flat=True)
    conversation_user_ids = set(sent_to) | set(received_from)
    
    conversations = []
    for other_user_id in conversation_user_ids:
        other_user = User.objects.get(id=other_user_id)
        # Get last message in this conversation
        last_message = DirectMessage.objects.filter(
            Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
        ).order_by('-created').first()
        # Count unread messages from this user
        unread_count = DirectMessage.objects.filter(
            sender=other_user, receiver=user, is_read=False
        ).count()
        conversations.append({
            'user': other_user,
            'last_message': last_message,
            'unread_count': unread_count,
        })
    
    # Sort by last message time (most recent first)
    conversations.sort(key=lambda x: x['last_message'].created if x['last_message'] else None, reverse=True)
    
    # Total unread count
    total_unread = DirectMessage.objects.filter(receiver=user, is_read=False).count()
    
    context = {
        'conversations': conversations,
        'total_unread': total_unread,
    }
    return render(request, 'base/inbox.html', context)


@login_required(login_url='login')
def conversation(request, pk):
    """Show conversation with a specific user and handle sending messages."""
    other_user = User.objects.get(id=pk)
    user = request.user
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            DirectMessage.objects.create(
                sender=user,
                receiver=other_user,
                content=content
            )
            return redirect('conversation', pk=pk)
    
    # Get all messages between these two users
    conversation_messages = DirectMessage.objects.filter(
        Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
    ).order_by('created')
    
    # Mark received messages as read
    DirectMessage.objects.filter(sender=other_user, receiver=user, is_read=False).update(is_read=True)
    
    context = {
        'other_user': other_user,
        'conversation_messages': conversation_messages,
    }
    return render(request, 'base/conversation.html', context)


@login_required(login_url='login')
def start_conversation(request):
    """Start a new conversation by selecting a user."""
    q = request.GET.get('q', '')
    
    # Search for users (exclude self)
    if q:
        users = User.objects.filter(
            Q(username__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
        ).exclude(id=request.user.id)[:20]
    else:
        users = User.objects.exclude(id=request.user.id)[:20]
    
    context = {
        'users': users,
        'q': q,
    }
    return render(request, 'base/start_conversation.html', context)


def get_unread_message_count(user):
    """Helper function to get unread message count for a user."""
    if not user.is_authenticated:
        return 0
    return DirectMessage.objects.filter(receiver=user, is_read=False).count()


@login_required(login_url='login')
def mentorship_profile(request):
    """Update the user's mentorship profile."""
    # Get or create mentor profile for current user
    mentor_profile, created = MentorProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = MentorProfileForm(request.POST, instance=mentor_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your mentorship profile has been updated!')
            return redirect('/home/?category=mentorship')
    else:
        form = MentorProfileForm(instance=mentor_profile)
    
    context = {
        'form': form,
        'mentor_profile': mentor_profile,
    }
    return render(request, 'base/mentorship_form.html', context)


@login_required(login_url='login')
def delete_mentorship_profile(request):
    """Delete the user's mentorship profile."""
    if request.method == 'POST':
        try:
            mentor_profile = MentorProfile.objects.get(user=request.user)
            mentor_profile.delete()
            messages.success(request, 'Your mentorship profile has been deleted.')
        except MentorProfile.DoesNotExist:
            messages.error(request, 'No mentorship profile found.')
    return redirect('/home/?category=mentorship')


def get_mentorship_data():
    """Get lists of available mentors and people seeking mentors."""
    available_mentors = MentorProfile.objects.filter(
        is_available_as_mentor=True
    ).select_related('user').order_by('-updated')
    
    seeking_mentors = MentorProfile.objects.filter(
        is_seeking_mentor=True
    ).select_related('user').order_by('-updated')
    
    return {
        'available_mentors': available_mentors,
        'seeking_mentors': seeking_mentors,
    }