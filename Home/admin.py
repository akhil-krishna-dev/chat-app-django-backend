from django.contrib import admin
from .models import Chat,Message




class ChatAdmin(admin.ModelAdmin):
    
    def display_participants(self, obj):
         return ", ".join(str(participant) for participant in obj.participants.all())
    display_participants.short_description = 'Participants'
    list_display = ('created_at', 'display_participants')

admin.site.register(Chat,ChatAdmin)


class MessageAdmin(admin.ModelAdmin):
     list_display = ( 'sender', 'content', 'status', 'file', 'image', 'audio')
admin.site.register(Message, MessageAdmin)

