from django.contrib import admin
from .models import Election, Position, Voter, Candidate, Vote, AuditLog

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'nomination_start_date', 'nomination_end_date', 'election_start_date', 'election_end_date']
    search_fields = ['title', 'description']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'election', 'number_of_people', 'duration']
    list_filter = ['election']
    search_fields = ['title']

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ['registration_number', 'email', 'election', 'has_voted', 'voted_at']
    list_filter = ['election', 'has_voted']
    search_fields = ['registration_number', 'email']

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'status', 'applied_at']
    list_filter = ['status', 'position']
    search_fields = ['name', 'user__email']

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['voter', 'candidate', 'position', 'voted_at']
    list_filter = ['position', 'voted_at']
    search_fields = ['voter__registration_number', 'candidate__name']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'user', 'voter_reg_no', 'election', 'ip_address']
    list_filter = ['action', 'election', 'timestamp']
    search_fields = ['voter_reg_no', 'details', 'user__username']
    readonly_fields = ['timestamp']
