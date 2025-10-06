from django.urls import path
from .views import RunPipelineView, MetricsView

urlpatterns = [
    path('api/run/', RunPipelineView.as_view(), name='pipeline-run'),
    path('api/metrics/', MetricsView.as_view(), name='pipeline-metrics'),
]