# ---------------------------------------------------------------------
# 1. ATIVAÇÃO DA API E VARIÁVEL PARA O SERVICE ACCOUNT
# ---------------------------------------------------------------------

# Ativa a API do Secret Manager
resource "google_project_service" "secretmanager_api" {
  project = var.gcp_project_id
  service = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Obtém o Service Account do Cloud Run (usado para acessar segredos)
# O Cloud Run usa um Service Account padrão por padrão, que é:
# {project_number}-compute@developer.gserviceaccount.com
# Ou o Service Account customizado se você o definir no cloud_run.tf.
data "google_iam_policy" "cloud_run_viewer_policy" {
  binding {
    role = "roles/secretmanager.secretAccessor"
    # O Cloud Run usa o Service Account do Compute Engine padrão do projeto
    # Se você usar um SA customizado, deve substituir esta expressão:
    members = [
      "serviceAccount:${google_cloud_run_v2_service.app_service.service_account}",
    ]
  }
}

# ---------------------------------------------------------------------
# 2. DEFINIÇÃO DOS SEGREDOs
# ---------------------------------------------------------------------

# Segredo 1: Chave Secreta do Django
resource "google_secret_manager_secret" "django_secret_key" {
  secret_id = "${var.app_name}-django-secret-key"
  project   = var.gcp_project_id
  replication {
    automatic = true
  }
  # Permite que o Service Account do Cloud Run acesse este segredo
  iam {
    policy_data = data.google_iam_policy.cloud_run_viewer_policy.policy_data
  }
  depends_on = [google_project_service.secretmanager_api]
}

# Cria a versão do segredo (a chave é gerada uma vez, manualmente ou via CI/CD)
# Para a primeira vez, podemos usar uma senha gerada aleatoriamente
resource "random_id" "django_secret_key_initial" {
  byte_length = 32
}
resource "google_secret_manager_secret_version" "django_secret_key_v1" {
  secret      = google_secret_manager_secret.django_secret_key.id
  # ATENÇÃO: Em produção, você deve remover secret_data e injetar a chave via CI/CD/gcloud,
  # para que ela não fique no estado do Terraform.
  secret_data = random_id.django_secret_key_initial.hex 
}


# Segredo 2: Senha do MySQL/Cloud SQL
resource "google_secret_manager_secret" "mysql_password" {
  secret_id = "${var.app_name}-mysql-password"
  project   = var.gcp_project_id
  replication {
    automatic = true
  }
  iam {
    policy_data = data.google_iam_policy.cloud_run_viewer_policy.policy_data
  }
}

# Versão do segredo: usa a senha gerada aleatoriamente no main.tf
resource "google_secret_manager_secret_version" "mysql_password_v1" {
  secret      = google_secret_manager_secret.mysql_password.id
  secret_data = random_password.db_password.result # Variável do main.tf
}


# Segredo 3: URI do MongoDB Atlas
resource "google_secret_manager_secret" "mongodb_uri" {
  secret_id = "${var.app_name}-mongodb-uri"
  project   = var.gcp_project_id
  replication {
    automatic = true
  }
  iam {
    policy_data = data.google_iam_policy.cloud_run_viewer_policy.policy_data
  }
}

# ATENÇÃO: A URI do MongoDB Atlas deve ser inserida MANUALMENTE 
# ou via um pipeline de provisionamento do Atlas/CI/CD, 
# pois o Terraform GCP não a conhece.

# Para fins de demonstração no Terraform, crie uma versão inicial
resource "google_secret_manager_secret_version" "mongodb_uri_initial" {
  secret = google_secret_manager_secret.mongodb_uri.id
  # SUBSTITUA ESTE VALOR PELA SUA URI REAL DO ATLAS. 
  # Se quiser evitar colocar a URI no código, você pode comentar este bloco
  # e inseri-la usando o gcloud CLI após o apply inicial do Terraform.
  secret_data = "mongodb+srv://user:password@clustername.mongodb.net/provision_mongo?retryWrites=true&w=majority"
}