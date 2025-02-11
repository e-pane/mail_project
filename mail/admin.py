from django.contrib import admin
from .models import Email
from .models import User  
from django.contrib.auth.admin import UserAdmin

class EmailAdmin(admin.ModelAdmin):
    list_display = ('user', 'sender', 'subject', 'body', 'timestamp', 'read', 'archived')

# Register your models here.
admin.site.register(Email, EmailAdmin)
admin.site.register(User, UserAdmin)
