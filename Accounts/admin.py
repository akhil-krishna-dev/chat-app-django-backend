from django.contrib import admin
from .models import CustomUser


class UserAdmin(admin.ModelAdmin):
    list_display = ['email','first_name', 'last_name']
admin.site.register(CustomUser, UserAdmin)
