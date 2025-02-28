import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Chat, Message
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from Accounts.models import CustomUser
from django.utils import timezone


class NotificatonConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.request_user = self.scope['user']
        self.notification_group_name = f'notification_{self.request_user.id}'

        await self.channel_layer.group_add(
            self.notification_group_name,
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
        message_type = data.get('type')
        payload_data = data.get('data')

        # text messages handling section -------------------->>>>>>>>>>>>>>>>>>>
        if message_type == "message":
            chat_id = payload_data.get("chatId")
            message = payload_data.get("message")
            message_data = await self.save_message(chat_id,message)
            target_user_id = message_data['target_user_id']
            target_user_group = f"notification_{target_user_id}"
            request_user_group = f"notification_{self.request_user.id}"
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

        # online status handling section -------------------->>>>>>>>>>>>>>>>>>>
        if message_type == "online":
            participant_id = payload_data['user_id']  
            target_user_group = f"notification_{participant_id}"
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                target_user_group,
                {
                    "type":"send_replay_online_status",
                    "data":{
                        "user_id":self.request_user.id
                    }
                }
            )
            
        # Video call handling section starts <<<<<<<<<<<---------->>>>>>>>>>>>>>>
        # offer received from caller section ---->>>>>>
        if message_type == "offer":
            offer = payload_data['offer']
            channel_layer = get_channel_layer()  
            target_user_group = f"notification_{payload_data['targetUserId']}"
            await channel_layer.group_send(
                target_user_group,
                {
                    "type":"send_webrtc_offer",
                    "data":{
                        "offer":offer,
                        "created_user_db_id":self.request_user.id
                    }
                }
            )

        # replay as answer from receiver section ----->>>>>>>
        if message_type == "answer":
            targetUserId = payload_data['targetUserId']
            answer = payload_data['answer']

            target_user_group = f"notification_{targetUserId}"
            channel_layer = get_channel_layer()

            await channel_layer.group_send(
                target_user_group,
                {
                    "type":"send_webrtc_answer",
                    "data":{
                        "answer":answer,
                        "received_user_db_id":self.request_user.id
                    }
                }
            )

        # sending ice-candidate ------->>>>>>>>>>
        if message_type == "ice-candidate":

            targetUserId = payload_data['targetUserId']
            candidate = payload_data["candidate"]

            target_user_group = f"notification_{targetUserId}"
            channel_layer = get_channel_layer()

            await channel_layer.group_send(
                target_user_group,
                {
                    "type":"send_ice_candidate",
                    "data":{
                        "candidate":candidate
                    }
                }
            )

        # call accept handle -------->>>>>>>>>>>>
        if message_type == "call-accepted":
            try:
                targetUserId = payload_data['targetUserId']

                target_user_group = f"notification_{targetUserId}"
                channel_layer = get_channel_layer()

                await channel_layer.group_send(
                    target_user_group,
                    {"type":"send_call_accepted_message"}
                )
            except:
                pass

        # webRTC disconnected handle ------->>>>>>>>>
        if message_type == "disconnected":
            try:
                targetUserId = payload_data['targetUserId']

                target_user_group = f"notification_{targetUserId}"
                channel_layer = get_channel_layer()

                await channel_layer.group_send(
                    target_user_group,
                    {"type":"send_disconnected_message"}
                )
            except:
                pass


    # Socket disconnecting area 
    # <<<<<<<<<<<<<<<<    ==========================   >>>>>>>>>>>>>>>>>>
    async def disconnect(self, close_code):
        await self.notify_online_users("send_offline_status",self.chat_related_users_id)

        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )

    #  all methods ---------------->>>>>>>>>>
    async def notify_online_users(self, type=None, participants = []):
        data =  {
            "user_id":self.request_user.id
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
    
    async def send_webrtc_offer(self, event):
        message = event['data']

        await self.send(text_data=json.dumps({
            "type":"webrtc_offer",
            "data":message
        }))

    async def send_webrtc_answer(self, event):
        message = event['data']

        await self.send(text_data=json.dumps({
            "type":"webrtc_answer",
            "data":message
        }))

    async def send_ice_candidate(self, event):
        message = event['data']
        await self.send(text_data=json.dumps({
            'type': 'candidate',
            'data':message
        }))

    async def handle_message_seen(self, event):
        data = event['data']
        await self.send(text_data=json.dumps({
                'type':'seen_message_ids',
                'data':data
            }))

    async def send_call_accepted_message(self, event):
        await self.send(json.dumps({
            "type":"call-accepted"
        }))

    async def send_disconnected_message(self, event):
        await self.send(text_data=json.dumps({
            "type":"disconnected"
        }))


    # ------------------->>>>>>>>>>>>>>>>>>>>>>>>
    # Databse operations ------------------------>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    @database_sync_to_async
    def save_message(self, chat_id, message):
       
        try:
            chat = Chat.objects.get(id=chat_id)
            message =  Message.objects.create(
                chat=chat, sender=self.request_user, content=message
            )
            participants = list(chat.participants.all())
            target_user = None
            if len(participants) == 2:
                if participants[0] == self.request_user:
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
    
    @database_sync_to_async
    def get_chat_related_users_id(self):
        try:
            chat = Chat.objects.filter(participants__id = self.request_user.id)
            users_id = []
            for c in chat:
                try:
                    users_id.append(c.participants.exclude(id=self.request_user.id).first().pk) 
                except Exception as e:
                    raise ValueError(f"an error found {e}")                   
            return users_id
        except Chat.DoesNotExist:
            raise ValueError("chat object not found")

    @database_sync_to_async
    def update_user_last_seen(self):                          
        user = CustomUser.objects.get(id=self.request_user.id)
        user.last_seen = timezone.now()
        user.save()
        return user.last_seen
    


