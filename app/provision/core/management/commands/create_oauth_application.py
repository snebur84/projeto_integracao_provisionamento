"""
Management command to create or show an OAuth2 Application (django-oauth-toolkit).

Usage:
  python app/provision/manage.py create_oauth_application --name "provision-client" --client-type confidential --grant-type client_credentials --scopes "provision read"

If an application with the same name exists, prints its client_id and client_secret (if available).
If not, creates one and prints the credentials.

Note: client_secret is only available for 'confidential' clients; for 'public' clients the secret will be blank.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import secrets

try:
    from oauth2_provider.models import get_application_model
except Exception:
    get_application_model = None

User = get_user_model()


class Command(BaseCommand):
    help = "Create or show an OAuth2 Application (django-oauth-toolkit)."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Name for the OAuth2 Application")
        parser.add_argument("--client-type", choices=["confidential", "public"], default="confidential")
        parser.add_argument("--grant-type", choices=["authorization-code", "implicit", "password", "client-credentials"], default="client-credentials")
        parser.add_argument("--user", help="Owner username (optional). If provided, the user must exist.")
        parser.add_argument("--scopes", help="Default scopes (space-separated), e.g. 'provision read'", default="provision")
        parser.add_argument("--redirect-uris", help="Redirect URIs (space-separated), used for authorization-code clients", default="")

    def handle(self, *args, **options):
        if get_application_model is None:
            raise CommandError("oauth2_provider is not installed. Install django-oauth-toolkit and run migrations.")

        Application = get_application_model()
        name = options["name"]
        client_type = options["client_type"]
        grant_type_opt = options["grant_type"]
        owner = None
        if options.get("user"):
            try:
                owner = User.objects.get(username=options["user"])
            except User.DoesNotExist:
                raise CommandError(f"User '{options['user']}' not found.")

        grant_type_map = {
            "authorization-code": Application.GRANT_AUTHORIZATION_CODE,
            "implicit": Application.GRANT_IMPLICIT,
            "password": Application.GRANT_PASSWORD,
            "client-credentials": Application.GRANT_CLIENT_CREDENTIALS,
        }
        grant_type = grant_type_map.get(grant_type_opt, Application.GRANT_CLIENT_CREDENTIALS)

        client_type_map = {
            "confidential": Application.CLIENT_CONFIDENTIAL,
            "public": Application.CLIENT_PUBLIC,
        }
        client_type_val = client_type_map.get(client_type, Application.CLIENT_CONFIDENTIAL)

        # try to find existing application by name
        app = Application.objects.filter(name=name).first()
        if app:
            self.stdout.write(self.style.SUCCESS(f"Application '{name}' already exists."))
            self.stdout.write(f"Client ID: {app.client_id}")
            # client_secret only available for confidential applications; may be empty if not created here
            secret = getattr(app, "client_secret", "")
            self.stdout.write(f"Client Secret: {secret or '(empty)'}")
            self.stdout.write(f"Client Type: {app.client_type}, Grant Type: {app.authorization_grant_type}")
            return

        # create a secret for confidential clients
        client_secret = secrets.token_urlsafe(32) if client_type_val == Application.CLIENT_CONFIDENTIAL else ""

        app = Application.objects.create(
            name=name,
            user=owner,
            client_type=client_type_val,
            authorization_grant_type=grant_type,
            client_secret=client_secret,
            redirect_uris=options.get("redirect_uris", ""),
        )
        self.stdout.write(self.style.SUCCESS(f"Application '{name}' created."))
        self.stdout.write(f"Client ID: {app.client_id}")
        self.stdout.write(f"Client Secret: {app.client_secret or '(empty)'}")
        self.stdout.write(f"Client Type: {app.client_type}, Grant Type: {app.authorization_grant_type}")
        if options.get("scopes"):
            self.stdout.write(f"Scopes (informational): {options.get('scopes')}")