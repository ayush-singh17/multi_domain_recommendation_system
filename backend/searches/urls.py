from django.urls import path
from .views import (
    RecommendView, PDFView,
    SearchHistoryView, SearchDeleteView,
    SavedJournalListCreateView, SavedJournalDeleteView,
    FeedbackCreateView, JournalCatalogView, JournalLinksView,
)

urlpatterns = [
    path("journals/", JournalCatalogView.as_view(), name="journal_catalog"),
    path("journal-links/", JournalLinksView.as_view(), name="journal_links"),
    path('recommend/',         RecommendView.as_view(),            name='recommend'),
    path('recommend/pdf/',     PDFView.as_view(),                  name='pdf'),
    path('history/',           SearchHistoryView.as_view(),        name='history'),
    path('history/<int:pk>/',  SearchDeleteView.as_view(),         name='history_delete'),
    path('saved/',             SavedJournalListCreateView.as_view(), name='saved'),
    path('saved/<int:pk>/',    SavedJournalDeleteView.as_view(),   name='saved_delete'),
    path('feedback/',          FeedbackCreateView.as_view(),       name='feedback'),
]

