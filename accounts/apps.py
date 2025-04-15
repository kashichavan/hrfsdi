from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'


# apps.py in your `accounts` app
def ready(self):
    import accounts.signals  # adjust app name if needed
