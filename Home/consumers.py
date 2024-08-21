import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Chat, Message
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from Accounts.models import CustomUser
from datetime import datetime



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        user = self.scope['user']

        if message:
            message_data = await self.save_message(user, message)
            target_user_id = message_data['target_user_id']
            target_user_group = f"notification_{target_user_id}"
            request_user_group = f"notification_{user.id}"
            channel_layer = get_channel_layer()  

            await channel_layer.group_send(
                request_user_group,
                {
                    'type': 'send_notification',
                    'message': message_data                  
                }
            )       
            
            message_data["is_receiver"] = True
            await channel_layer.group_send(
                target_user_group,
                {
                    "type":"send_notification",
                    "message":message_data
                }
            )

    async def online_message(self, event):
        message = event['message']       
        await self.send(text_data=json.dumps({"online":message}))

    @database_sync_to_async
    def save_message(self, user, message):
        
        try:
            chat = Chat.objects.get(id=self.chat_id)
            message =  Message.objects.create(chat=chat, sender=user, content=message)
            participants = list(chat.participants.all())
            target_user = None
            if len(participants) == 2:
                if participants[0] == user:
                    target_user = participants[1]
                else:
                    target_user = participants[0]
            else:
                raise ValueError("participants not found")                

            message_data ={
                "id":message.pk,
                "chat_id":message.chat.pk,
                "sender":{"id":message.sender.pk},
                "content":message.content,
                "status":message.status,
                "timestamp":str(message.timestamp),
                "target_user_id":target_user.id,
                "is_receiver":False
            }
            return message_data
        
        except Chat.DoesNotExist:
            raise ValueError("chat object not found")
        
        except Exception as e:
            raise ValueError(f"an error occured {e}")
    

    async def handle_message_seen(self, event):
        data = event['data']
        await self.send(text_data=json.dumps({
                'type':'seen_message_ids',
                'data':data
            }))



class NotificatonConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['user'].id
        self.chat_group_name = f'notification_{self.user_id}'

        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            "data":"connected"
        }))
        self.chat_related_users_id = await self.get_chat_related_users_id()
        await self.notify_online_users("send_online_status",self.chat_related_users_id)

    async def receive(self, text_data=None):
        data = json.loads(text_data)
        type = data.get('type')
        payload_data = data.get('data')

        if type == "new_chat_user":
            participant_id = payload_data['user_id'] 
            notification_group = f"notification_{participant_id}"
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                notification_group,
                {
                    "type":"new_chat_online_status",
                    "data":{
                        "user_id":self.user_id
                    }
                }
            )

        if type == "online":
            participant_id = payload_data['user_id']  
            notification_group = f"notification_{participant_id}"
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                notification_group,
                {
                    "type":"send_replay_online_status",
                    "data":{
                        "user_id":self.user_id
                    }
                }
            )
            

    async def disconnect(self, close_code):
        await self.notify_online_users("send_offline_status",self.chat_related_users_id)

        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def get_chat_related_users_id(self):
        try:
            chat = Chat.objects.filter(participants__id = self.user_id)
            users_id = []
            for c in chat:
                try:
                    users_id.append(c.participants.exclude(id=self.user_id).first().pk) 
                except Exception as e:
                    raise ValueError(f"an error found {e}")                   
            return users_id
        except Chat.DoesNotExist:
            raise ValueError("chat object not found")

    async def notify_online_users(self, type=None, participants = []):
        data =  {
            "user_id":self.user_id
        }
        if type=='send_offline_status':
            last_seen = await self.update_user_last_seen()
            data['last_seen'] = str(last_seen)
        for participant_id in participants:
            notification_group = f"notification_{participant_id}"
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                notification_group,
                {
                    "type":type,
                    "data":data
                }
            )

    @database_sync_to_async
    def update_user_last_seen(self):                          
        user = CustomUser.objects.get(id=self.user_id)
        user.last_seen = datetime.utcnow()
        user.save()
        return user.last_seen.now()


    async def new_chat_online_status(self, event):
        data = event['data']
        await self.send(text_data=json.dumps({
            "type":"online",
            "data":data
        }))

    async def send_online_status(self, event):
        await self.send(text_data=json.dumps({
            "type":"online",
            "data":event['data']
        }))

    async def send_offline_status(self, event):
        await self.send(text_data=json.dumps({
            "type":"offline",
            "data":event['data']
        }))

    async def send_replay_online_status(self, event):
        await self.send(text_data=json.dumps({
            "type":"replay_from_online_user",
            "data":event['data']
        }))

    async def handle_chat_first_message(self, event):
        data = event['data']
        user_id = event['user_id']
        await self.send(text_data=json.dumps({
            "type":"new_chat",
            "data":data,
            "user_id":user_id
        }))

    async def send_notification(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            "type":"message_notification",
            "data":message
        }))

