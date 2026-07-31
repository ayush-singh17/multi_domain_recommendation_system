from rest_framework import serializers
from .models import Search, SavedJournal, Feedback


class SearchSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Search
        fields = ['id', 'abstract', 'focus', 'search_mode', 'keywords', 'created_at']
        read_only_fields = ['id', 'created_at']


class SavedJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SavedJournal
        fields = ['id', 'journal_title', 'issn', 'quartile', 'sjr',
                  'h_index', 'plan', 'notes', 'saved_at']
        read_only_fields = ['id', 'saved_at']


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Feedback
        fields = ['id', 'feedback_type', 'rating', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']

