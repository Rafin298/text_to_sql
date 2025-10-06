import time

from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import Text2SQLRequestSerializer
from .services.gemini_client import GeminiWrapper
from .services.sql_sanitizer import basic_sanitize_and_enforce, SQLSanitizerError
from .models import QueryLog
import pandas as pd


class Text2SQLAPIView(APIView):
    """
    POST /api/text2sql/
    body: { nl_query: str, schema: optional str, format: "json"|"dataframe_csv" }
    """

    permission_classes = []  # wire permissions as you need

    def post(self, request):
        serializer = Text2SQLRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        nl_query = data["nl_query"]
        schema_hint = data.get("schema", "")
        out_format = data.get("format", "json")
        max_rows = data.get("max_rows", 1000)

        log = QueryLog.objects.create(nl_query=nl_query, status="running")
        start = time.time()

        try:
            gem = GeminiWrapper()
            raw_sql = gem.nl_to_sql(nl_query=nl_query, schema_hint=schema_hint)
            log.generated_sql = raw_sql
            log.save()

            # sanitize & enforce SELECT-only + LIMIT
            sql = basic_sanitize_and_enforce(raw_sql, max_rows)
            print(f"Sanitized SQL: {sql}")  # for debugging
            # Execute with statement_timeout set (milliseconds)
            with connection.cursor() as cursor:
                # set local statement_timeout for this transaction (5s = 5000ms)
                cursor.execute("SET LOCAL statement_timeout = %s", ["5000"])
                # Execute query
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description] if cursor.description else []
                rows = cursor.fetchall()

            runtime = time.time() - start
            log.status = "success"
            log.meta = {"runtime_s": runtime, "row_count": len(rows)}
            log.save()

            # Format results
            results = [dict(zip(columns, r)) for r in rows]

            if out_format == "dataframe_csv":
                if pd is None:
                    return Response(
                        {"error": "pandas is not installed on server."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                df = pd.DataFrame(results)
                csv = df.to_csv(index=False)
                return Response(
                    {"csv": csv, "rows": len(results)},
                    status=status.HTTP_200_OK
                )

            return Response(
                {"sql": sql, "rows": results, "meta": log.meta},
                status=status.HTTP_200_OK
            )

        except SQLSanitizerError as e:
            log.status = "rejected"
            log.error = str(e)
            log.save()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle DB timeouts or other runtime errors
            log.status = "error"
            log.error = str(e)
            log.save()
            return Response(
                {"error": "Execution failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )