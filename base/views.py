from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from .models import Room, Topic, Message, User, PostVote
from .forms import RoomForm, UserForm, MyUserCreationForm


JOBS_REFERRALS_SLUG = 'jobs-referrals'


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
        return redirect('home')

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
            return redirect('home')
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

    university_domain = getattr(settings, 'UNIVERSITY_EMAIL_DOMAIN', 'youruni.edu')
    return render(request, 'base/login_register.html', {'form': form, 'university_domain': university_domain})

@login_required(login_url='login')
def home(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''
    topic_slug = request.GET.get('topic') if request.GET.get('topic') is not None else ''

    if topic_slug == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
        messages.error(request, 'Jobs & Referrals is a demo paid category. Enable demo access to view it.')
        return redirect('home')

    rooms = Room.objects.all()
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

    context = {'rooms': rooms, 'topics': topics, 'room_count': room_count, 'room_messages': room_messages}
    return render(request, 'base/home.html', context)


@login_required(login_url='login')
def room(request, pk):
    room = Room.objects.get(id=pk)

    if getattr(room.topic, 'slug', None) == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
        messages.error(request, 'Jobs & Referrals is a demo paid category. Enable demo access to view and comment.')
        return redirect('home')

    score = room.votes.aggregate(score=Coalesce(Sum('value'), 0))['score']
    room_messages = room.message_set.all().order_by('-created')
    participants = room.participants.all()
    if request.method == 'POST':
        if getattr(room.topic, 'slug', None) == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
            messages.error(request, 'Demo paid access is required to comment in Jobs & Referrals.')
            return redirect('home')
        message = Message.objects.create(
            user = request.user,
            room = room,
            body = request.POST.get('body')
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
    context = {'user': user, 'rooms': rooms, 'room_messages': room_messages, 'topics': topics}
    return render(request, 'base/profile.html', context)


@login_required(login_url= 'login')
def createRoom(request):
    form = RoomForm()
    topics = _restrict_jobs_referrals_topics(Topic.objects.all(), request.user)
    if request.method == 'POST':
        topic_id = request.POST.get('topic')
        topic = Topic.objects.filter(id=topic_id).first()
        if not topic:
            messages.error(request, 'Please select a valid category.')
            return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': None})

        if topic.slug == JOBS_REFERRALS_SLUG and not _user_can_access_jobs_referrals(request.user):
            messages.error(request, 'Demo paid access is required to post in Jobs & Referrals.')
            return render(request, 'base/room_form.html', {'form': form, 'topics': topics, 'room': None})

        Room.objects.create(
            host = request.user,
            topic = topic,
            name = request.POST.get('name'),
            description = request.POST.get('description'),
        )

        return redirect('home')

    context = {'form': form, 'topics': topics}
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
            messages.error(request, 'Demo paid access is required to post in Jobs & Referrals.')
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
        messages.error(request, 'Demo paid access is required for Jobs & Referrals.')
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
    messages.success(request, 'Demo paid access enabled. You can now access Jobs & Referrals.')
    return redirect('user-profile', pk=request.user.id)


@login_required(login_url='login')
def demoUnsubscribe(request):
    if request.method != 'POST':
        return redirect('user-profile', pk=request.user.id)
    request.user.is_paid = False
    request.user.save(update_fields=['is_paid'])
    messages.success(request, 'Demo paid access disabled.')
    return redirect('user-profile', pk=request.user.id)