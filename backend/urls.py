from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        "message": "E-Voting Backend API",
        "status": "running",
        "endpoints": {
            "admin": "/admin/",
            "auth": "/api/auth/",
            "elections": "/api/",
            "positions": "/api/positions/",
            "voters": "/api/voters/",
            "candidates": "/api/candidates/",
            "voting": "/api/voting/"
        }
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('election.urls')),
]
