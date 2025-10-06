from rest_framework import serializers


class Text2SQLRequestSerializer(serializers.Serializer):
    nl_query = serializers.CharField()
    schema = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional DB schema snippet to give the model context."
    )
    format = serializers.ChoiceField(
        choices=("json", "dataframe_csv"),
        default="json"
    )
    max_rows = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=1000,
        default=1000
    )