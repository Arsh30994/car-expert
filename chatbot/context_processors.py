from django.conf import settings


def local_demo_mode(request):
    """Expose only the local showcase flag; never enable it in production."""
    return {"local_demo_mode": settings.LOCAL_DEMO_MODE}
