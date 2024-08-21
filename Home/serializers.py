from rest_framework import serializers
from .pagination import MessagePagination
from .models import Chat, Message
from Accounts.serializers import UserProfileSerializer
import os

class MessageSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer()
    image = serializers.SerializerMethodField()
    file_details = serializers.SerializerMethodField()
    audio = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'image', 'file', 'audio','file_details', 'timestamp', 'status']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_audio(self, obj):
        request = self.context.get('request')
        if obj.audio and request:
            return request.build_absolute_uri(obj.audio.url)
        return None
    
    def get_file_details(self, object):
        try:
            if object.file: 
                data = {
                    "file_name":os.path.basename(object.file.name),
                    "file_size":object.file.size
                }              
                return data           
        except FileNotFoundError:
            return None
        return None


class ChatSerializer(serializers.ModelSerializer):
    participants = UserProfileSerializer(many=True)
    messages = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField(read_only=True, default=0)
    last_message = MessageSerializer(read_only=True)

    class Meta:
        model = Chat
        fields = ['id', 'participants', 'messages','unread','last_message']

    def get_messages(self, obj):
        request = self.context.get('request')
        paginator = MessagePagination()
        messages = obj.messages.all()
        page = paginator.paginate_queryset(messages, request)
        
        if page is not None:
            serialized_data = MessageSerializer(page, many=True, context={"request":request}).data
            serialized_data.sort(key=lambda message:message['timestamp'])
            return paginator.get_paginated_response(serialized_data).data
        return MessageSerializer(messages, many=True).data
    
    def get_unread(self, obj):
        request_user = self.context['request'].user
        return obj.messages.exclude(sender = request_user).filter(status="never seen").count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by("-timestamp").first()
        return MessageSerializer(last_msg).data if last_msg else None

