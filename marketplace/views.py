from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def discover_view(request):
    return render(request, "marketplace/discover.html")
