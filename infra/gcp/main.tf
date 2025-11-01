# ---------------------------------------------------------------------
# 1. CONFIGURAÇÃO DO PROVEDOR E BACKEND (Cloud Storage)
# ---------------------------------------------------------------------

terraform {
  # Defina a versão mínima do Terraform
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Configuração do Backend para armazenar o estado no GCS (Recomendado para CI/CD)
  # ATENÇÃO: O bucket 'tf-state-provision' deve ser criado ANTES de rodar o Terraform pela primeira vez.
  backend "gcs" {
    bucket = "tf-state-provision-bucket" # SUBSTITUA pelo nome único do seu bucket de estado
    prefix = "terraform/state/provision-app"
  }
}

# Configuração do provedor GCP
provider "google" {
  # O projeto e região serão injetados via variáveis de ambiente/GitHub Actions
  # project = var.gcp_project_id
  # region  = var.gcp_region
}

# ---------------------------------------------------------------------
# 2. VARIÁVEIS DE CONFIGURAÇÃO (Definição)
# ---------------------------------------------------------------------

variable "gcp_project_id" {
  description = "ID do projeto GCP onde os recursos serão criados."
  type        = string
}

variable "gcp_region" {
  description = "Região principal do GCP (ex: us-central1)."
  type        = string
  default     = "us-central1" # Sugestão, ajuste conforme sua necessidade
}

variable "app_name" {
  description = "Nome base para os recursos da aplicação (Cloud Run service, DB, etc.)"
  type        = string
  default     = "provision-app"
}

# ---------------------------------------------------------------------
# 3. GOOGLE CLOUD SQL (MYSQL)
# ---------------------------------------------------------------------

# Geração de uma senha segura e aleatória para o usuário do banco de dados
resource "random_password" "db_password" {
  length  = 20
  special = true
  override_special = "!@#$%^&*"
}

resource "google_sql_database_instance" "mysql_instance" {
  database_version = "MYSQL_8_0"
  name             = "${var.app_name}-db-instance"
  project          = var.gcp_project_id
  region           = var.gcp_region
  
  settings {
    tier = "db-f1-micro" # Escolha o tier adequado para produção/dev. f1-micro é para testes
    # Ativa auto-resize
    disk_autoresize = true
    # Configurações de rede
    ip_configuration {
      # Usaremos IP Privado para maior segurança (requer VPC Connector)
      ipv4_enabled    = false 
      private_network = google_compute_network.vpc_network.id
    }
    # Backup
    backup_configuration {
      enabled            = true
      binary_log_enabled = true
    }
    # Manutenção
    maintenance_window {
      day  = 7 # Domingo
      hour = 2 # 2 AM
    }
  }
}

# Criação do banco de dados dentro da instância
resource "google_sql_database" "default_database" {
  name     = "provision_db" # Nome usado no settings.py
  instance = google_sql_database_instance.mysql_instance.name
}

# Criação do usuário do banco de dados
resource "google_sql_user" "db_user" {
  name     = "provision_user" # Nome usado no settings.py
  instance = google_sql_database_instance.mysql_instance.name
  host     = "%"
  password = random_password.db_password.result
}

# ---------------------------------------------------------------------
# 4. REDE (VPC E CONNECTOR)
# Necessário para Cloud SQL IP Privado e potencialmente MongoDB Atlas VPC Peering
# ---------------------------------------------------------------------

# Rede VPC padrão (Se você já tem uma VPC, pode usar um data source)
resource "google_compute_network" "vpc_network" {
  name                    = "${var.app_name}-vpc"
  auto_create_subnetworks = true
}

# Sub-rede para o VPC Access Connector (usado pelo Cloud Run)
resource "google_compute_subnetwork" "connector_subnet" {
  name          = "${var.app_name}-connector-subnet"
  ip_cidr_range = "10.8.0.0/28" # Range pequeno e dedicado
  region        = var.gcp_region
  network       = google_compute_network.vpc_network.id
  private_ip_google_access = true # Permite acesso a APIs do Google via Private IP
}

# Conector de acesso VPC Serverless
resource "google_vpc_access_connector" "vpc_connector" {
  name          = "${var.app_name}-vpc-connector"
  project       = var.gcp_project_id
  region        = var.gcp_region
  ip_cidr_range = google_compute_subnetwork.connector_subnet.ip_cidr_range
  network       = google_compute_network.vpc_network.id
  # O throughput é importante para o desempenho
  min_throughput = 200 # Mbps
  max_throughput = 300 # Mbps
}