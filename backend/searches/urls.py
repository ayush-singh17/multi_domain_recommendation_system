from django.urls import path
from .views import (
    RecommendView, PDFView,
    SearchHistoryView, SearchDeleteView,
    SavedJournalListCreateView, SavedJournalDeleteView,
)

urlpatterns = [
    path('recommend/',         RecommendView.as_view(),            name='recommend'),
    path('recommend/pdf/',     PDFView.as_view(),                  name='pdf'),
    path('history/',           SearchHistoryView.as_view(),        name='history'),
    path('history/<int:pk>/',  SearchDeleteView.as_view(),         name='history_delete'),
    path('saved/',             SavedJournalListCreateView.as_view(), name='saved'),
    path('saved/<int:pk>/',    SavedJournalDeleteView.as_view(),   name='saved_delete'),
]
