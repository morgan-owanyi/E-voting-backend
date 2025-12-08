from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Count
from .models import Election, Position, Voter, Candidate, Vote
from .serializers import ElectionSerializer, PositionSerializer, VoterSerializer, CandidateSerializer, VoteSerializer
from accounts.models import EmailOTP
import random


class ElectionViewSet(viewsets.ModelViewSet):
    queryset = Election.objects.all()
    serializer_class = ElectionSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Position.objects.all()
        election_id = self.request.query_params.get('election', None)
        if election_id:
            queryset = queryset.filter(election_id=election_id)
        return queryset


class VoterViewSet(viewsets.ModelViewSet):
    queryset = Voter.objects.all()
    serializer_class = VoterSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        voters_data = request.data.get('voters', [])
        election_id = request.data.get('election')
        
        if not election_id:
            return Response({'error': 'Election ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        voters = []
        for voter_data in voters_data:
            # Handle both old format (string) and new format (dict with email)
            if isinstance(voter_data, dict):
                reg_no = voter_data.get('registration_number')
                email = voter_data.get('email', '')
            else:
                reg_no = voter_data
                email = ''
            
            voters.append(Voter(
                election_id=election_id,
                registration_number=reg_no,
                email=email
            ))
        
        Voter.objects.bulk_create(voters, ignore_conflicts=True)
        return Response({'message': f'{len(voters)} voters added successfully'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        reg_no = request.data.get('regNo')
        election_id = request.data.get('election')
        
        try:
            voter = Voter.objects.get(registration_number=reg_no, election_id=election_id)
            return Response({'valid': True, 'has_voted': voter.has_voted})
        except Voter.DoesNotExist:
            return Response({'valid': False}, status=status.HTTP_404_NOT_FOUND)


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Candidate.objects.all()
        position_id = self.request.query_params.get('position', None)
        status_filter = self.request.query_params.get('status', None)
        
        if position_id:
            queryset = queryset.filter(position_id=position_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset

    @action(detail=False, methods=['post'])
    def apply(self, request):
        # Auto-populate name and email from logged-in user
        data = request.data.copy()
        if 'name' not in data or not data.get('name'):
            data['name'] = f'{request.user.first_name} {request.user.last_name}'.strip() or request.user.username
        if 'email' not in data or not data.get('email'):
            data['email'] = request.user.email
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        candidate = self.get_object()
        candidate.status = 'approved'
        candidate.reviewed_by = request.user
        candidate.reviewed_at = timezone.now()
        candidate.save()
        return Response({'message': 'Candidate approved successfully'})

    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        candidate = self.get_object()
        candidate.status = 'rejected'
        candidate.rejection_reason = request.data.get('reason', '')
        candidate.reviewed_by = request.user
        candidate.reviewed_at = timezone.now()
        candidate.save()
        return Response({'message': 'Candidate rejected'})




# Import clean VotingViewSet from separate file
from .voting_views import VotingViewSet
