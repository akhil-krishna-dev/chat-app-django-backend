from django.db.models import Max
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics
from Accounts.serializers import UserProfileSerializer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import re


User = get_user_model()



class UsersList(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        queryset = list(filter(self.user_filter, User.objects.all()))
        return queryset
    
    def user_filter(self, user):
        if user.is_superuser or user.id == self.request.user.id:
            return None
        
        query = self.request.query_params.get('query', None)
        if query:
            words = query.replace(" ", "")
            username = user.first_name + user.last_name
            pattern = re.compile(re.escape(words), re.IGNORECASE)
            if pattern.search(username) or pattern.search(username):
                return user
            return None
        return user
        


class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user).annotate(
            last_message_timestamp = Max('messages__timestamp')
    ).order_by('-last_message_timestamp')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        chat = self.get_object()
        sender = request.user
        content = request.data.get('content')

        if not content:
            return Response({"error": "Content cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(chat=chat, sender=sender, content=content)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def send_image_file(self, request, pk=None):
        chat = self.get_object()
        sender = request.user
        images = []

        for key in request.FILES:
            images.append(request.FILES[key])

        if not images:
            return Response({"error":"images cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        message_list = []
        for image in images:
            message = Message.objects.create(chat=chat, sender=sender, image=image)
            serialized_msg = MessageSerializer(message , context={"request":self.request}).data
            serialized_msg['chat_id'] = chat.id
            message_list.append(serialized_msg)

        chat_serializer = chat.participants.all()

        other_user_id = None
        for p in chat_serializer:
            if p.id != request.user.id:
                other_user_id = p.id
        
        channel_layer = get_channel_layer()
        group_name = f"notification_{other_user_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,{
                'type':'send_notification',
                'message':message_list,
            }
        )

        return Response(message_list, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def send_any_file(self, request, pk=None):
        chat = self.get_object()
        sender = request.user
        files = []

        for key in request.FILES:
            files.append(request.FILES[key])

        if not files:
            return Response({"error":"files cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
        
        message_list = []
        for file in files:
            message = Message.objects.create(chat=chat, sender=sender, file=file)
            msg_serializer = MessageSerializer(message , context={"request":self.request}).data
            msg_serializer['chat_id'] = chat.id
            message_list.append(msg_serializer)

        chat_participants = chat.participants.all()
        
        other_user_id = None
        for p in chat_participants:
            if p.id != sender.id:
                other_user_id = p.id

        channel_layer = get_channel_layer()
        group_name = f"notification_{other_user_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,{
                'type':'send_notification',
                'message':message_list,
            }
        )

        return Response(message_list, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def send_voice_message(self, request, pk=None):
        chat = self.get_object()
        sender = request.user
        audio = request.FILES['audio']
        
        message = Message.objects.create(chat=chat, sender=sender, audio=audio)

        chat_participants = chat.participants.all()
        
        other_user_id = None
        for p in chat_participants:
            if p.id != sender.id:
                other_user_id = p.id

        serialized_message = MessageSerializer(message , context={"request":self.request}).data

        serialized_message['chat_id'] = chat.id

        channel_layer = get_channel_layer()
        group_name = f"notification_{other_user_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,{
                'type':'send_notification',
                'message':serialized_message,
            }
        )

        return Response(serialized_message, status=status.HTTP_201_CREATED)
    

    @action(detail=True, methods=['post'])
    def make_all_message_seen(self, request, pk=None):
        chat = self.get_object()
        filtered_by_chat = Message.objects.filter(chat=chat, status="never seen")
        messages = filtered_by_chat.exclude(sender=request.user)
        
        for message in messages:
            try :
                message.status = "seen"
                message.save()
            except Message.DoesNotExist:
                pass
            except Exception as e:
                raise e

        return Response({"message":"all messages changed as seen"})

    @action(detail=False, methods=['post'])
    def handle_message_seen(self, request):
        message_ids = request.data.get('seenMsgIds')
        chat_id = request.data.get('chatId')

        channel_layer = get_channel_layer()
        group_name = f"chat_{chat_id}"

        for i in message_ids:
            try :
                message = Message.objects.get(id=int(i))
                message.status = "seen"
                message.save()
            except Message.DoesNotExist:
                pass
            except Exception as e:
                raise e

        async_to_sync(channel_layer.group_send)(
            group_name,{
                'type':'handle_message_seen',
                'data':{
                    'message_ids':message_ids,
                    'chat_id':int(chat_id)
                }
            }
        )

        return Response({"message":"success"}, status=status.HTTP_200_OK)

        

    def create(self, request, *args, **kwargs):
        participants = request.data.get('participants')

        if not participants:
            return Response({"error": "Participants cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        participant_objects = User.objects.filter(id__in=participants)
        if not participant_objects.exists():
            return Response({'error': 'Invalid participant IDs'}, status=400)
        
        other_user = None
        for p in participant_objects:
            if p != request.user:
                other_user = p

        if other_user:
            chat = Chat.objects.filter(participants=request.user).filter(participants=other_user).first()
            if chat:
                data = {
                    "id":str(chat.id)
                }
                return Response(data, status=status.HTTP_200_OK)

        chat = Chat.objects.create()
        chat.participants.set(participants)
        chat.save()

        serializer = ChatSerializer(chat , context={"request":self.request})

        other_user_id = None

        for p in serializer.data['participants']:
            if p['id'] != request.user.id:
                other_user_id = p['id']
                
        channel_layer = get_channel_layer()
        group_name = f"notification_{other_user_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,{
                'type':'handle_chat_first_message',
                'data':serializer.data,
                "user_id":request.user.id
            }
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
