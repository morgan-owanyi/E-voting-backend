from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),   # <-- THIS LINE IS REQUIRED
    path('api/election/', include('election.urls')),   # <-- THIS LINE IS REQUIRED
    path('api-auth/', include('rest_framework.urls')),  # optional, for browsable API login
    path('api/token/', include('rest_framework.authtoken.urls')),  # optional, for token auth
]