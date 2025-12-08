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


class VotingViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def request_otp(self, request):
        from django.core.mail import send_mail
        from django.conf import settings
        
        reg_no = request.data.get('regNo')
        election_id = request.data.get('election')

        try:
            voter = Voter.objects.get(registration_number=reg_no, election_id=election_id)

            if voter.has_voted:
                return Response({'error': 'You have already voted'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not voter.email:
                return Response({'error': 'No email associated with this voter'}, status=status.HTTP_400_BAD_REQUEST)

            # Generate or retrieve OTP using EmailOTP model
            EmailOTP.objects.filter(email=voter.email, used=False).update(used=True)
            otp_obj = EmailOTP.create_otp(email=voter.email, length=6, expiry_seconds=600)
            
            # Send OTP via email
            try:
                email_body = f"""Hello,

Your One-Time Password (OTP) for voting is: {otp_obj.code}

IMPORTANT: This OTP can only be used once and will expire in 10 minutes.
Election: {voter.election.title}
Registration Number: {voter.registration_number}

Please do not share this OTP with anyone.

Thank you,
KuraVote Team"""
                
                send_mail(
                    subject=f'Your Voting OTP - {voter.election.title}',
                    message=email_body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kuravote.com'),
                    recipient_list=[voter.email],
                    fail_silently=False,
                )
                
                return Response({
                    'message': 'OTP sent successfully to your registered email',
                    'email_hint': voter.email[:3] + '***' + voter.email[voter.email.index('@'):]
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to send OTP email: {str(e)}',
                    'otp': otp_obj.code
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Voter.DoesNotExist:
            return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        reg_no = request.data.get('regNo')
        otp = request.data.get('otp')
        election_id = request.data.get('election')

        try:
            voter = Voter.objects.get(registration_number=reg_no, election_id=election_id)
            
            if not voter.email:
                return Response({'error': 'No email associated with this voter'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify OTP from database
            try:
                otp_obj = EmailOTP.objects.get(email=voter.email, code=otp, used=False)
                
                if not otp_obj.is_valid():
                    return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Mark OTP as used
                otp_obj.mark_used()
                
                return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
                
            except EmailOTP.DoesNotExist:
                return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Voter.DoesNotExist:
            return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)

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


    @action(detail=False, methods=['get'])
    def export_results_csv(self, request):
        import csv
        from django.http import HttpResponse
        
        election_id = request.query_params.get('election')
        election = Election.objects.get(id=election_id)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="results_{election.title}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Position', 'Candidate', 'Votes', 'Percentage'])
        
        positions = Position.objects.filter(election_id=election_id)
        
        for position in positions:
            candidates = Candidate.objects.filter(
                position=position,
                status='approved'
            ).annotate(vote_count=Count('votes_received'))
            
            total_votes = sum(c.vote_count for c in candidates)
            
            for candidate in candidates:
                percentage = (candidate.vote_count / total_votes * 100) if total_votes > 0 else 0
                writer.writerow([
                    position.title,
                    candidate.name,
                    candidate.vote_count,
                    f"{percentage:.2f}%"
                ])
        
        return response

    @action(detail=False, methods=['get'])
    def export_results_pdf(self, request):
        from django.http import HttpResponse
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        
        election_id = request.query_params.get('election')
        election = Election.objects.get(id=election_id)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph(f"Election Results: {election.title}", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Election info
        info_style = styles['Normal']
        elements.append(Paragraph(f"<b>Generated:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))
        elements.append(Spacer(1, 0.3*inch))
        
        positions = Position.objects.filter(election_id=election_id)
        
        for position in positions:
            # Position title
            pos_style = ParagraphStyle('PositionTitle', parent=styles['Heading2'], textColor=colors.HexColor('#283593'))
            elements.append(Paragraph(position.title, pos_style))
            elements.append(Spacer(1, 0.2*inch))
            
            candidates = Candidate.objects.filter(
                position=position,
                status='approved'
            ).annotate(vote_count=Count('votes_received')).order_by('-vote_count')
            
            total_votes = sum(c.vote_count for c in candidates)
            
            # Results table
            data = [['Rank', 'Candidate', 'Votes', 'Percentage']]
            for idx, candidate in enumerate(candidates, 1):
                percentage = (candidate.vote_count / total_votes * 100) if total_votes > 0 else 0
                data.append([
                    str(idx),
                    candidate.name,
                    str(candidate.vote_count),
                    f"{percentage:.2f}%"
                ])
            
            table = Table(data, colWidths=[0.7*inch, 3*inch, 1*inch, 1.3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (3, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.4*inch))
        
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="results_{election.title}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response

    @action(detail=False, methods=['get'])
    def export_turnout_csv(self, request):
        import csv
        from django.http import HttpResponse
        
        election_id = request.query_params.get('election')
        election = Election.objects.get(id=election_id)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="turnout_{election.title}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        
        total_voters = Voter.objects.filter(election_id=election_id).count()
        voted_count = Voter.objects.filter(election_id=election_id, has_voted=True).count()
        turnout_rate = (voted_count / total_voters * 100) if total_voters > 0 else 0
        
        writer.writerow(['Total Registered Voters', total_voters])
        writer.writerow(['Total Votes Cast', voted_count])
        writer.writerow(['Voters Yet to Vote', total_voters - voted_count])
        writer.writerow(['Turnout Rate', f"{turnout_rate:.2f}%"])
        writer.writerow([''])
        
        # Voting timeline
        writer.writerow(['Registration Number', 'Email', 'Voted', 'Voted At'])
        voters = Voter.objects.filter(election_id=election_id).order_by('-voted_at')
        for voter in voters:
            writer.writerow([
                voter.registration_number,
                voter.email or 'N/A',
                'Yes' if voter.has_voted else 'No',
                voter.voted_at.strftime('%Y-%m-%d %H:%M:%S') if voter.voted_at else 'N/A'
            ])
        
        return response

    @action(detail=False, methods=['get'])
    def export_audit_log_csv(self, request):
        import csv
        from django.http import HttpResponse
        from .models import AuditLog
        
        election_id = request.query_params.get('election')
        election = Election.objects.get(id=election_id)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_log_{election.title}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Action', 'User', 'Voter Reg No', 'Details', 'IP Address'])
        
        logs = AuditLog.objects.filter(election_id=election_id)
        for log in logs:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.get_action_display(),
                log.user.username if log.user else 'System',
                log.voter_reg_no or 'N/A',
                log.details,
                log.ip_address or 'N/A'
            ])
        
        return response


