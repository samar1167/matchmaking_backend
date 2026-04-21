from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def get_user_for_token(token):
    if not token:
        return AnonymousUser()

    authenticator = JWTAuthentication()
    try:
        validated_token = authenticator.get_validated_token(token)
        return authenticator.get_user(validated_token)
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token = self._token_from_headers(scope) or self._token_from_query_string(scope)
        scope['user'] = await get_user_for_token(token)
        return await self.app(scope, receive, send)

    def _token_from_headers(self, scope):
        headers = dict(scope.get('headers') or [])
        authorization = headers.get(b'authorization', b'').decode()
        if authorization.lower().startswith('bearer '):
            return authorization.split(' ', 1)[1].strip()
        return None

    def _token_from_query_string(self, scope):
        query_string = scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [None])[0]
        return token.strip() if token else None
