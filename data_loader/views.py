from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PipelineRunSerializer, MetricsSerializer
from django.conf import settings
from .management.commands.load_csvs import CSVLoader

# Simple in-memory last-run store; for production persist to DB.
LAST_RUN = {}

class RunPipelineView(APIView):
    def post(self, request):
        serializer = PipelineRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_root = serializer.validated_data.get('csv_root') or getattr(settings, 'CSV_ROOT', None)
        create_missing = serializer.validated_data.get('create_missing_parents', False)

        loader = CSVLoader(csv_root=csv_root, create_missing_parents=create_missing)
        report = loader.run()
        # store last run
        LAST_RUN['report'] = report
        return Response(report, status=status.HTTP_200_OK)

class MetricsView(APIView):
    def get(self, request):
        report = LAST_RUN.get('report')
        if not report:
            return Response({'detail': 'No run found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MetricsSerializer(report)
        return Response(serializer.data)