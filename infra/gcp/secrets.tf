# Define um Service Account (SA) para o Cloud Run. 
# Necessário para referenciar o SA nas permissões de acesso ao Secret Manager.
resource "google_service_account" "cloud_run_sa" {
  account_id   = "sa-${var.app_name}"
  display_name = "Service Account for ${var.app_name} Cloud Run"
}

# ---------------------------------------------------------------------
# 1. DEFINIÇÃO DOS SECRETS
# ---------------------------------------------------------------------

# 1.1. Secret MONGODB_URI (Para conexão com banco NoSQL)
resource "google_secret_manager_secret" "mongodb_uri" {
  secret_id = "mongodb-uri"
  project   = var.gcp_project_id

  replication {
    automatic = true
  }
}
# NOTA: O valor da MONGODB_URI deve ser inserido manualmente no GCP ou por um script/CI pipeline separado.

# 1.2. Secret DJANGO_SECRET_KEY (Gerado randomicamente e seguro)
resource "random_password" "django_secret_key_value" {
  length  = 50
  special = true
  override_special = "!@#$%^&*()_+"
}

resource "google_secret_manager_secret" "django_secret_key" {
  secret_id = "django-secret-key"
  project   = var.gcp_project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "django_secret_key_version" {
  secret      = google_secret_manager_secret.django_secret_key.id
  secret_data = random_password.django_secret_key_value.result
}

# 1.3. Secret MYSQL_PASSWORD (Para o Cloud SQL)
# Assume que random_password.mysql_password_value está definido no main.tf
resource "google_secret_manager_secret" "mysql_password" {
  secret_id = "mysql-db-password"
  project   = var.gcp_project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "mysql_password_version" {
  secret      = google_secret_manager_secret.mysql_password.id
  # Assume que random_password.mysql_password_value está no main.tf
  secret_data = random_password.mysql_password_value.result 
}

# ---------------------------------------------------------------------
# 2. IAM BINDINGS (Permite ao Cloud Run SA acessar todos os secrets)
# ---------------------------------------------------------------------

locals {
  cloud_run_sa_email = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "mongodb_uri_access" {
  secret_id = google_secret_manager_secret.mongodb_uri.id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.cloud_run_sa_email
}

resource "google_secret_manager_secret_iam_member" "django_key_access" {
  secret_id = google_secret_manager_secret.django_secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.cloud_run_sa_email
}

resource "google_secret_manager_secret_iam_member" "mysql_password_access" {
  secret_id = google_secret_manager_secret.mysql_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.cloud_run_sa_email
}