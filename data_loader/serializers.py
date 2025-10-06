from rest_framework import serializers

class PipelineRunSerializer(serializers.Serializer):
    csv_root = serializers.CharField(required=False, allow_blank=True)
    create_missing_parents = serializers.BooleanField(default=False)

class MetricsSerializer(serializers.Serializer):
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
    duration_seconds = serializers.FloatField()
    processed = serializers.DictField(child=serializers.IntegerField())
    inserted = serializers.DictField(child=serializers.IntegerField())
    errors = serializers.DictField(child=serializers.IntegerField())
    referential_violations = serializers.DictField(child=serializers.IntegerField())
    null_counts = serializers.DictField(child=serializers.IntegerField())