from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Add custom fields
    birth_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    def __str__(self):
        return self.username
    
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

# Create Profile when a new user is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
