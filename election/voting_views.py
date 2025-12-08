"""
Clean Voting Views for OTP-based voting
This file contains ONLY the VotingViewSet with clean, organized methods
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import Voter, Vote, Candidate
from .otp_service import OTPService
import logging

logger = logging.getLogger(__name__)


class VotingViewSet(viewsets.ViewSet):
    """
    ViewSet for voter authentication and voting via OTP
    """
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def request_otp(self, request):
        """
        Request an OTP for voter authentication.
        
        Request body:
            {
                "regNo": "voter_registration_number",
                "election": election_id
            }
        
        Response (success):
            {
                "message": "OTP sent successfully...",
                "email_hint": "abc***@example.com"
            }
        
        Response (email failed - fallback):
            {
                "message": "OTP generated successfully",
                "otp": "123456",
                "note": "Email service unavailable...",
                "email_failed": true
            }
        """
        reg_no = request.data.get('regNo')
        election_id = request.data.get('election')
        
        # Validate input
        if not reg_no or not election_id:
            return Response(
                {'error': 'Registration number and election ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find voter
            voter = Voter.objects.get(
                registration_number=reg_no,
                election_id=election_id
            )
            
            # Check if already voted
            if voter.has_voted:
                logger.warning(f"Voter {reg_no} attempted to vote again")
                return Response(
                    {'error': 'You have already voted in this election'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if voter has email
            if not voter.email:
                return Response(
                    {'error': 'No email address associated with your voter registration'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate OTP
            otp_obj = OTPService.generate_otp(voter.email)
            
            # Try to send email
            email_result = OTPService.send_otp_email(
                email=voter.email,
                otp_code=otp_obj.code,
                election_title=voter.election.title,
                reg_no=reg_no
            )
            
            # Return appropriate response
            if email_result['success']:
                return Response({
                    'message': 'OTP sent successfully to your registered email',
                    'email_hint': OTPService.get_masked_email(voter.email)
                }, status=status.HTTP_200_OK)
            else:
                # Email failed - return OTP in response for fallback display
                logger.info(f"Email failed for {voter.email}, returning OTP in response")
                return Response({
                    'message': 'OTP generated successfully',
                    'otp': otp_obj.code,
                    'note': 'Email service is temporarily unavailable. Please use the OTP code displayed on your screen.',
                    'email_failed': True
                }, status=status.HTTP_200_OK)
        
        except Voter.DoesNotExist:
            logger.warning(f"Voter not found: {reg_no} for election {election_id}")
            return Response(
                {'error': 'Voter registration not found. Please contact the election administrator.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in request_otp: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """
        Verify an OTP code for a voter.
        
        Request body:
            {
                "regNo": "voter_registration_number",
                "otp": "123456",
                "election": election_id
            }
        
        Response:
            {
                "message": "OTP verified successfully"
            }
        """
        reg_no = request.data.get('regNo')
        otp_code = request.data.get('otp')
        election_id = request.data.get('election')
        
        # Validate input
        if not reg_no or not otp_code or not election_id:
            return Response(
                {'error': 'Registration number, OTP, and election ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find voter
            voter = Voter.objects.get(
                registration_number=reg_no,
                election_id=election_id
            )
            
            # Check if voter has email
            if not voter.email:
                return Response(
                    {'error': 'No email address associated with your voter registration'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify OTP
            verification_result = OTPService.verify_otp(voter.email, otp_code)
            
            if verification_result['valid']:
                logger.info(f"OTP verified for voter {reg_no}")
                return Response(
                    {'message': verification_result['message']},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': verification_result['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Voter.DoesNotExist:
            logger.warning(f"Voter not found during OTP verification: {reg_no}")
            return Response(
                {'error': 'Voter registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in verify_otp: {str(e)}")
            return Response(
                {'error': 'An error occurred while verifying your OTP'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def cast(self, request):
        """
        Cast votes for a voter after OTP verification.
        
        Request body:
            {
                "regNo": "voter_registration_number",
                "votes": {
                    "position_id": "candidate_id",
                    ...
                },
                "election": election_id
            }
        
        Response:
            {
                "message": "Vote cast successfully",
                "votes_count": 3
            }
        """
        reg_no = request.data.get('regNo')
        votes_data = request.data.get('votes', {})
        election_id = request.data.get('election')
        
        # Validate input
        if not reg_no or not election_id:
            return Response(
                {'error': 'Registration number and election ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not votes_data:
            return Response(
                {'error': 'No votes provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find voter
            voter = Voter.objects.get(
                registration_number=reg_no,
                election_id=election_id
            )
            
            # Check if already voted
            if voter.has_voted:
                logger.warning(f"Voter {reg_no} attempted to vote multiple times")
                return Response(
                    {'error': 'You have already voted in this election'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate all candidates exist
            for position_id, candidate_id in votes_data.items():
                try:
                    Candidate.objects.get(
                        id=candidate_id,
                        position_id=position_id,
                        position__election_id=election_id,
                        status='approved'
                    )
                except Candidate.DoesNotExist:
                    return Response(
                        {'error': f'Invalid candidate selection for position {position_id}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Cast all votes
            votes_cast = []
            for position_id, candidate_id in votes_data.items():
                vote = Vote.objects.create(
                    voter=voter,
                    candidate_id=candidate_id,
                    position_id=position_id
                )
                votes_cast.append(vote)
            
            # Mark voter as voted
            voter.has_voted = True
            voter.voted_at = timezone.now()
            voter.save()
            
            logger.info(f"Voter {reg_no} successfully cast {len(votes_cast)} votes")
            
            return Response({
                'message': 'Vote cast successfully',
                'votes_count': len(votes_cast)
            }, status=status.HTTP_201_CREATED)
        
        except Voter.DoesNotExist:
            logger.warning(f"Voter not found during vote casting: {reg_no}")
            return Response(
                {'error': 'Voter registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in cast: {str(e)}")
            return Response(
                {'error': 'An error occurred while casting your vote'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
