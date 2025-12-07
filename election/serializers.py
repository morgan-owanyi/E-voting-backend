from rest_framework import serializers
from .models import Election, Position, Voter, Candidate, Vote

class ElectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'


class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = '__all__'
        read_only_fields = ['has_voted', 'voted_at']


class CandidateSerializer(serializers.ModelSerializer):
    position_title = serializers.CharField(source='position.title', read_only=True)
    
    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['user', 'status', 'reviewed_at', 'reviewed_by']


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = '__all__'
        read_only_fields = ['voted_at']
