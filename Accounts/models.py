from django.db import models
from django.contrib.auth.models import UserManager,AbstractUser
import os



class CustomUserManager(UserManager):

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("email required !")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("superuser must have is_staff=True !")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("superuser must have is_superuser=True !")
        
        return self._create_user(email, password, **extra_fields)
    


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    image = models.ImageField(null=True, blank=True, upload_to='users/profile_images', default='users/default/default_profile.jpg')
    status = models.CharField(max_length=255, null=True, blank=True, default="Available")
    last_seen = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return str(self.email)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()


    def save(self, *args, **kwargs):
        try:
            old_image = CustomUser.objects.get(id=self.pk).image
        except CustomUser.DoesNotExist:
            old_image = None

        if old_image and self.image and old_image != self.image:
            default_image_path = 'users/default/default_profile.jpg'    
            if default_image_path != old_image.path:
                if os.path.isfile(old_image.name):
                    os.remove(old_image.path)
        return super().save(*args,**kwargs)



class BlacklistedToken(models.Model):
    token = models.CharField(max_length=500, unique=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token

        






