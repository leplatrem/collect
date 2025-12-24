import logging

from django.http import HttpResponseServerError, JsonResponse


logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """
    Responds to /health/ with a 200 OK and JSON payload.

    Useful for Docker, CI/CD, load balancers, etc.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return JsonResponse({"status": "ok"})

        if request.path == "/readiness/":
            return self.readiness(request)

        return self.get_response(request)

    def readiness(self, request):
        # Connect to each database and do a generic standard SQL query
        # that doesn't write any data and doesn't depend on any tables
        # being present.
        # Source: https://www.ianlewis.org/en/kubernetes-health-checks-django
        try:
            from django.db import connections

            for name in connections:
                cursor = connections[name].cursor()
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                assert row is not None and row[0] == 1, (
                    f"Invalid response from database ({row})"
                )
        except Exception as exc:
            logger.exception(exc)
            return HttpResponseServerError("db: cannot connect to database.")
        return JsonResponse({"status": "ok"})
