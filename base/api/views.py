from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from base.models import Room
from .serializers import RoomSerializer


JOBS_REFERRALS_SLUG = 'jobs-referrals'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getRoutes(request):
    routes = [
        'GET /api',
        'GET /api/rooms',
        'GET /api/rooms/:id'
    ]
    return Response(routes)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getRooms(request):
    rooms = Room.objects.all()
    if not getattr(request.user, 'is_paid', False):
        rooms = rooms.exclude(topic__slug=JOBS_REFERRALS_SLUG)
    serializer = RoomSerializer(rooms, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getRoom(request, pk):
    room = Room.objects.get(id=pk)
    if getattr(room.topic, 'slug', None) == JOBS_REFERRALS_SLUG and not getattr(request.user, 'is_paid', False):
        return Response({'detail': 'Premium access required for Jobs & Referrals.'}, status=status.HTTP_403_FORBIDDEN)
    serializer = RoomSerializer(room, many=False)
    return Response(serializer.data)