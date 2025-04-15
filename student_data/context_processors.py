# myapp/context_processors.py
def user_info(request):
    if request.user.is_authenticated:
        return {
            'user_full_name': request.user.get_full_name(),
            'user_role': 'Administrator' if request.user.is_superuser else 'User'
        }
    return {}