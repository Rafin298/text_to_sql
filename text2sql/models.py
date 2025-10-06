from django.db import models
from django.db.models import JSONField


class QueryLog(models.Model):
    """
    Minimal log of NL -> SQL runs for auditing and debugging.
    Store prompt, generated_sql, status, error, runtime, and result summary.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    nl_query = models.TextField()
    generated_sql = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, default="created")
    error = models.TextField(blank=True, null=True)
    meta = JSONField(blank=True, null=True)

    def __str__(self):
        return f"QueryLog #{self.id} {self.status}"