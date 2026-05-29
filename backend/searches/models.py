"""
Searches App — Models
Stores search history and saved journals per user.
"""

from django.db import models
from django.conf import settings


class Search(models.Model):
    """Every time a user searches, we save the abstract, focus, and search mode."""
    user        = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='searches')
    abstract    = models.TextField(blank=True, default='')
    focus       = models.CharField(max_length=100, default='General / Best Fit')
    search_mode = models.CharField(max_length=20, default='abstract')   # 'abstract' | 'keyword'
    keywords    = models.TextField(blank=True, default='')              # JSON list, e.g. '["ml","nlp"]'
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.created_at.strftime('%Y-%m-%d %H:%M')} ({self.search_mode})"


class SavedJournal(models.Model):
    """A journal a user explicitly saved from their results."""
    user          = models.ForeignKey(settings.AUTH_USER_MODEL,
                                      on_delete=models.CASCADE,
                                      related_name='saved_journals')
    search        = models.ForeignKey(Search,
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='saved_journals')
    journal_title = models.CharField(max_length=500)
    issn          = models.CharField(max_length=50, blank=True)
    quartile      = models.CharField(max_length=10, blank=True)
    sjr           = models.FloatField(null=True, blank=True)
    h_index       = models.IntegerField(null=True, blank=True)
    plan          = models.CharField(max_length=1, blank=True)   # A, B, or C
    notes         = models.TextField(blank=True)
    saved_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at']
        unique_together = ['user', 'issn']   # can't save same journal twice

    def __str__(self):
        return f"{self.user.email} — {self.journal_title}"
