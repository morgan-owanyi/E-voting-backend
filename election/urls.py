from django.urls import path
from .views import ElectionListCreateView, ElectionDetailView

urlpatterns = [
    path('', ElectionListCreateView.as_view(), name='election-list-create'),
    path('<int:pk>/', ElectionDetailView.as_view(), name='election-detail'),
]
