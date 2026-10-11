"""Keep private CRM responses out of caches and CRM searches out of access logs."""
import logging
from starlette.middleware.base import BaseHTTPMiddleware


class LeadAccessLogFilter(logging.Filter):
    def filter(self, record):
        # Uvicorn access format: client, method, path-with-query, version, status.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            values = list(record.args)
            if str(values[2]).split('?', 1)[0].startswith('/api/leads'):
                values[2] = '/api/leads/[private]'
                record.args = tuple(values)
        return True


class LeadPrivacyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path == '/api/leads' or request.url.path.startswith('/api/leads/'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Pragma'] = 'no-cache'
        return response
