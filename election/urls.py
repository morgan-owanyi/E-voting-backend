from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ElectionViewSet, PositionViewSet, VoterViewSet, CandidateViewSet, VotingViewSet

router = DefaultRouter()
router.register(r'elections', ElectionViewSet, basename='election')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'voters', VoterViewSet, basename='voter')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'voting', VotingViewSet, basename='voting')

urlpatterns = [
    path('', include(router.urls)),
]
