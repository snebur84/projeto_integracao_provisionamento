# ---------------------------------------------------------------------
# 1. ARTIFACT REGISTRY E GCS BUCKET (Para estáticos/mídia)
# ---------------------------------------------------------------------

# Repositório para armazenar a imagem Docker da aplicação
resource "google_artifact_registry_repository" "repo" {
  location      = var.gcp_region
  repository_id = "${var.app_name}-repo"
  description   = "Docker repository for the Cloud Run service"
  format        = "DOCKER"
}

# Bucket do Google Cloud Storage para servir arquivos estáticos e de mídia
resource "google_storage_bucket" "static_files" {
  name          = "${var.app_name}-static-files-${var.gcp_project_id}" 
  project       = var.gcp_project_id
  location      = var.gcp_region
  force_destroy = true 

  uniform_bucket_level_access = true 
  
  cors {
    origin      = ["*"]
    method      = ["GET", "HEAD"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}

# Politica de IAM para leitura pública do bucket (Necessário para Static Files)
resource "google_storage_bucket_iam_member" "public_reader" {
  bucket = google_storage_bucket.static_files.name
  role   = "organizations/825417857245/roles/gcp-storage-legacyObjectReader"
  member = "allUsers"
}


# ---------------------------------------------------------------------
# 2. CLOUD RUN SERVICE (Agora com injeção de segredos)
# ---------------------------------------------------------------------

# Serviço Cloud Run
resource "google_cloud_run_v2_service" "app_service" {
  name     = var.app_name
  location = var.gcp_region
  project  = var.gcp_project_id

  template {
    # Referência ao Service Account, usado no secrets.tf para IAM
    service_account = "sa-${var.app_name}@${var.gcp_project_id}.iam.gserviceaccount.com" # Exemplo de SA customizado

    containers {
      image = "${google_artifact_registry_repository.repo.location}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.repo.repository_id}/${var.app_name}:latest" 
      
      resources {
        cpu_idle = true
        memory   = "512Mi" 
        cpu      = 1
      }
      
      # INJEÇÃO DE VARIÁVEIS DE AMBIENTE E SECRETS
      env = [
        # Variáveis de Configuração Direta
        {
          name  = "DJANGO_DEBUG"
          value = "0" # Sempre desativado em produção
        },
        {
          name  = "DJANGO_ALLOWED_HOSTS"
          value = "*.run.app,127.0.0.1" # Adicione domínios customizados aqui
        },
        {
          name  = "CLOUD_SQL_INSTANCE_CONNECTION_NAME"
          value = google_sql_database_instance.mysql_instance.connection_name # Saída do main.tf
        },
        {
          name  = "MYSQL_DATABASE"
          value = "provision_db" # Valor fixo (definido no main.tf)
        },
        {
          name  = "MYSQL_USER"
          value = "provision_user" # Valor fixo (definido no main.tf)
        },
        {
          name  = "GS_BUCKET_NAME"
          value = google_storage_bucket.static_files.name # Saída do cloud_run.tf
        },

        # Variáveis injetadas do Secret Manager
        {
          name  = "DJANGO_SECRET_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.django_secret_key.secret_id
              version = "latest"
            }
          }
        },
        {
          name  = "MYSQL_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.mysql_password.secret_id
              version = "latest"
            }
          }
        },
        {
          name  = "MONGODB_URI"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.mongodb_uri.secret_id
              version = "latest"
            }
          }
        },
      ]
    }
    
    # Conexão ao VPC Access Connector 
    vpc_access {
      connector = google_vpc_access_connector.vpc_connector.id
      egress    = "ALL_TRAFFIC" 
    }

    # Conexão ao Cloud SQL (Unix Socket)
    cloud_sql_instance {
      instances = [google_sql_database_instance.mysql_instance.connection_name]
    }
    
    timeout = "300s"
    
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Permite acesso não autenticado (público) ao serviço Cloud Run
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.app_service.location
  name     = google_cloud_run_v2_service.app_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cria um Service Account customizado (opcional, mas recomendado para IAM seguro)
resource "google_service_account" "cloud_run_sa" {
  account_id   = "sa-${var.app_name}"
  display_name = "Service Account for ${var.app_name} Cloud Run"
}