# accounts/backends.py

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with either 
    username or email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find a user matching the username/email
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
            
            # Check the password
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # No user was found with the given username/email
            return None
        
        # Wrong password
        return None