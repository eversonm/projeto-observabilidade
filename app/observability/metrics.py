from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "products_http_requests_total",
    "Total HTTP requests handled by the products API",
    ["method", "route", "status_class"],
)
HTTP_DURATION = Histogram(
    "products_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
INCIDENT_RECOVERY = Histogram(
    "products_incident_recovery_duration_seconds",
    "Duration from alert firing to resolution (MTTR input)",
    ["alert_name"],
    buckets=(30, 60, 120, 300, 600, 1800, 3600, 14400, 86400),
)

