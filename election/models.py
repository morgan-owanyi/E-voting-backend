from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.

class Election(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    nomination_start_date = models.DateTimeField()
    nomination_end_date = models.DateTimeField()
    election_start_date = models.DateTimeField()
    election_end_date = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='elections_created', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Position(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=200)
    description = models.TextField()
    number_of_people = models.IntegerField(default=1)
    duration = models.CharField(max_length=100)
    caution = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} - {self.election.title}"


class Voter(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='voters')
    registration_number = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    has_voted = models.BooleanField(default=False)
    voted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['election', 'registration_number']

    def __str__(self):
        return f"{self.registration_number} - {self.election.title}"


class Candidate(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidacies')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    program = models.CharField(max_length=200)
    message = models.TextField()
    profile_photo = models.ImageField(upload_to='candidate_photos/', null=True, blank=True)
    manifesto = models.FileField(upload_to='manifestos/', null=True, blank=True)
    verification_documents = models.FileField(upload_to='verification_docs/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    applied_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_candidates')

    def __str__(self):
        return f"{self.name} - {self.position.title}"


class Vote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes_received')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='votes')
    voted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['voter', 'position']

    def __str__(self):
        return f"Vote for {self.candidate.name} by {self.voter.registration_number}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('VOTE_CAST', 'Vote Cast'),
        ('VOTER_ADDED', 'Voter Added'),
        ('CANDIDATE_APPROVED', 'Candidate Approved'),
        ('CANDIDATE_REJECTED', 'Candidate Rejected'),
        ('ELECTION_CREATED', 'Election Created'),
        ('POSITION_CREATED', 'Position Created'),
        ('OTP_REQUESTED', 'OTP Requested'),
        ('OTP_VERIFIED', 'OTP Verified'),
    ]
    
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    voter_reg_no = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} at {self.timestamp}"
