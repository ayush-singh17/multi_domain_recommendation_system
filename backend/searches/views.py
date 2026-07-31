"""
Searches App — Views

Endpoints:
  POST /api/search/recommend/     → call ML service, save to history
  GET  /api/search/history/       → list user's past searches
  DELETE /api/search/history/<id>/ → delete a search
  POST /api/search/recommend/pdf/ → get PDF from ML service
  GET  /api/search/saved/         → list saved journals
  POST /api/search/saved/         → save a journal
  DELETE /api/search/saved/<id>/  → remove a saved journal
"""

import requests
from django.conf                 import settings
from rest_framework              import generics, permissions, status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from django.http                 import HttpResponse
from .models                     import Search, SavedJournal, Feedback
from .serializers                import SearchSerializer, SavedJournalSerializer, FeedbackSerializer


ML_URL = settings.ML_SERVICE_URL


class RecommendView(APIView):
    """
    POST /api/search/recommend/
    Calls ML service, saves search to history, returns results.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        abstract    = request.data.get('abstract', '').strip()
        focus       = request.data.get('focus', 'General / Best Fit')
        search_mode = request.data.get('search_mode', 'abstract')
        keywords    = request.data.get('keywords', [])

        if search_mode == 'abstract' and not abstract:
            return Response({'error': 'Abstract is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if search_mode == 'keyword' and not keywords:
            return Response({'error': 'At least one keyword is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Call ML service
        try:
            ml_response = requests.post(
                f"{ML_URL}/recommend",
                json={
                    'abstract':    abstract,
                    'focus':       focus,
                    'search_mode': search_mode,
                    'keywords':    keywords,
                },
                timeout=60,
            )
            ml_response.raise_for_status()
            result = ml_response.json()
        except requests.exceptions.ConnectionError:
            return Response(
                {'error': 'ML service is not running. Start it with: uvicorn main:app --port 8001'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except requests.exceptions.Timeout:
            return Response(
                {'error': 'ML service timed out. Try a shorter abstract.'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            return Response({'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save to search history
        import json
        Search.objects.create(
            user        = request.user,
            abstract    = abstract,
            focus       = focus,
            search_mode = search_mode,
            keywords    = json.dumps(keywords) if keywords else '',
        )

        return Response(result, status=status.HTTP_200_OK)


class PDFView(APIView):
    """
    POST /api/search/recommend/pdf/
    Calls ML service PDF endpoint and streams the file back to React.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        abstract    = request.data.get('abstract', '').strip()
        focus       = request.data.get('focus', 'General / Best Fit')
        search_mode = request.data.get('search_mode', 'abstract')
        keywords    = request.data.get('keywords', [])

        if search_mode == 'abstract' and not abstract:
            return Response({'error': 'Abstract is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if search_mode == 'keyword' and not keywords:
            return Response({'error': 'At least one keyword is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            ml_response = requests.post(
                f"{ML_URL}/pdf",
                json={
                    'abstract':    abstract,
                    'focus':       focus,
                    'search_mode': search_mode,
                    'keywords':    keywords,
                },
                timeout=60,
            )
            ml_response.raise_for_status()
        except Exception as e:
            return Response({'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(
            ml_response.content,
            content_type='application/pdf',
        )
        response['Content-Disposition'] = (
            ml_response.headers.get('Content-Disposition',
                                    'attachment; filename=report.pdf')
        )
        return response


class SearchHistoryView(generics.ListAPIView):
    """GET /api/search/history/ — returns logged-in user's search history."""
    serializer_class   = SearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Search.objects.filter(user=self.request.user)


class SearchDeleteView(generics.DestroyAPIView):
    """DELETE /api/search/history/<id>/ — delete a search from history."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Search.objects.filter(user=self.request.user)


class SavedJournalListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/search/saved/ — list saved journals
    POST /api/search/saved/ — save a journal
    """
    serializer_class   = SavedJournalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedJournal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedJournalDeleteView(generics.DestroyAPIView):
    """DELETE /api/search/saved/<id>/ — remove a saved journal."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedJournal.objects.filter(user=self.request.user)


class FeedbackCreateView(generics.CreateAPIView):
    """
    POST /api/search/feedback/
    Submit feedback (bug report, feature request, or general comment).
    """
    serializer_class   = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

