from django.http import JsonResponse
from django.views.decorators.http import require_GET
from oauth2_provider.decorators import protected_resource
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@require_GET
@protected_resource(scopes=["read"])
def whoami(request, *args, **kwargs):
    """
    Example protected endpoint that returns basic info about the authenticated user/token.

    Usage:
      - Use an OAuth2 access token as Bearer token in Authorization header.
      - The endpoint requires the 'read' scope (see OAUTH2_PROVIDER['SCOPES']).
    """
    user = getattr(request, "user", None)
    token = getattr(request, "oauth2_provider_token", None) or getattr(request, "auth", None)
    data = {
        "username": getattr(user, "username", None),
        "email": getattr(user, "email", None),
        "is_authenticated": bool(user and user.is_authenticated),
        "token_present": bool(token),
        "timestamp": timezone.now().isoformat(),
    }
    logger.debug("whoami called: %s", data)
    return JsonResponse(data)