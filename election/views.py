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
    permission_classes = [IsAuthenticated]

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
        for reg_no in voters_data:
            voters.append(Voter(
                election_id=election_id,
                registration_number=reg_no
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
        serializer = self.get_serializer(data=request.data)
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


class VotingViewSet(viewsets.ViewSet):
    
    @action(detail=False, methods=['post'])
    def request_otp(self, request):
        reg_no = request.data.get('regNo')
        election_id = request.data.get('election')
        
        try:
            voter = Voter.objects.get(registration_number=reg_no, election_id=election_id)
            
            if voter.has_voted:
                return Response({'error': 'You have already voted'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate OTP
            otp_code = ''.join(str(random.randint(0, 9)) for _ in range(6))
            
            # In production, send OTP via email/SMS
            # For now, return it in response (REMOVE IN PRODUCTION)
            return Response({
                'message': 'OTP sent successfully',
                'otp': otp_code  # REMOVE IN PRODUCTION
            }, status=status.HTTP_200_OK)
            
        except Voter.DoesNotExist:
            return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        reg_no = request.data.get('regNo')
        otp = request.data.get('otp')
        
        # In production, verify OTP from database
        # For now, accept any 6-digit code
        if len(otp) == 6 and otp.isdigit():
            return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def cast(self, request):
        reg_no = request.data.get('regNo')
        votes_data = request.data.get('votes', {})
        election_id = request.data.get('election')
        
        try:
            voter = Voter.objects.get(registration_number=reg_no, election_id=election_id)
            
            if voter.has_voted:
                return Response({'error': 'You have already voted'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Cast votes
            for position_id, candidate_id in votes_data.items():
                Vote.objects.create(
                    voter=voter,
                    candidate_id=candidate_id,
                    position_id=position_id
                )
            
            # Mark voter as voted
            voter.has_voted = True
            voter.voted_at = timezone.now()
            voter.save()
            
            return Response({'message': 'Vote cast successfully'}, status=status.HTTP_201_CREATED)
            
        except Voter.DoesNotExist:
            return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def results(self, request):
        election_id = request.query_params.get('election')
        
        positions = Position.objects.filter(election_id=election_id)
        results = []
        
        for position in positions:
            candidates_results = Candidate.objects.filter(
                position=position,
                status='approved'
            ).annotate(
                vote_count=Count('votes_received')
            ).order_by('-vote_count')
            
            results.append({
                'position': position.title,
                'candidates': [{
                    'id': c.id,
                    'name': c.name,
                    'votes': c.vote_count
                } for c in candidates_results]
            })
        
        return Response(results, status=status.HTTP_200_OK)
