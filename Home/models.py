from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save,m2m_changed
from django.dispatch import receiver


User = get_user_model()

class Chat(models.Model):
    participants = models.ManyToManyField(User, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.pk) + " " + str(self.participants.all())
    
    
    

class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to="users/shared/images", null=True, blank=True)
    file = models.FileField(upload_to="users/shared/files", null=True, blank=True)
    audio = models.FileField(upload_to="users/shared/audio_files", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=250, default="never seen")

    def __str__(self):
        return f"{self.chat.id} {self.sender}"
    
    

# signals
@receiver(m2m_changed, sender=Chat.participants.through)
def create_chat_creation_method(sender, instance,action,**kwargs):
    if action == 'post_add':
        if instance.participants.exists():
            sender_user = instance.participants.first()
            Message.objects.create(
                chat=instance,
                sender=sender_user,
                content="You are now connected with ",
                status="chat created"
            )


