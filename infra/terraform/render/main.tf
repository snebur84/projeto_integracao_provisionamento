# infra/terraform/render/main.tf
# Cria um project, um serviço web (Django) e opcionalmente um serviço privado Postgres (como private service)
# Ajuste valores (repo/branch/region/plan) conforme sua conta Render e necessidades.
# Atenção: este arquivo assume o provider render-oss/render conforme provider.tf presente no repositório.

# Projeto que agrupa os serviços (ambientes)
resource "render_project" "project" {
  name = var.service_name

  # Exemplo de environments map — ajuste conforme sua política
  environments = {
    production = {
      name = "production"
      protected_status = false
    }
  }
}

# Serviço privado que provê Postgres (opcional, criado quando var.create_postgres = true)
# Observação: alguns fluxos preferem criar um "database" gerenciado pelo Render; este exemplo usa um private service
# com imagem oficial do Postgres para compatibilidade com o provider render-oss/render usado neste repo.
resource "render_private_service" "postgres" {
  count      = var.create_postgres ? 1 : 0
  project_id = render_project.project.id

  name = "${var.service_name}-postgres"

  # runtime_source.image block (exemplo): executa imagem postgres diretamente
  runtime_source {
    image = {
      image = "postgres:15-alpine"
    }
  }

  plan   = "starter"   # ajuste conforme necessidade (p.ex. starter, professional)
  region = "oregon"    # ajuste conforme sua conta

  # Exemplo simples de variáveis de ambiente para inicializar o container postgres
  # Notar: expor senhas em terraform state/outputs pode não ser desejável. Preferir secrets/Render dashboard.
  env = {
    POSTGRES_DB       = var.postgres_database
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
  }

  # Se necessário, conecte esse serviço ao environment do projeto
  environment_id = render_project.project.environments["production"].id
}

# Serviço web para a aplicação Django (build via Dockerfile no repositório)
resource "render_web_service" "provision" {
  count      = var.create_service ? 1 : 0
  project_id = render_project.project.id

  name = var.service_name

  # Build via Dockerfile no repositório
  runtime_source {
    docker = {
      # caminho para o Dockerfile no repositório (ajuste se necessário)
      dockerfile_path = "Dockerfile"
      # build_context = "." # se o provider exigir
    }
  }

  # Comando de start (ajuste conforme seu Dockerfile / Gunicorn config)
  start_command = "gunicorn provision.wsgi:application --bind 0.0.0.0:$PORT"

  # Branch do repo a ser utilizado (ajuste conforme seu fluxo)
  branch = "main"

  # Região do serviço (ajuste conforme sua conta)
  region = "oregon"

  # Variáveis de ambiente iniciais (a workflow irá injetar DATABASE_URL, MONGODB_URL e DJANGO_SETTINGS_MODULE)
  env = {
    # Colocar placeholders/valores mínimos aqui; o workflow CI atualiza/insere os env vars reais
    DJANGO_SETTINGS_MODULE = "provision.settings_render"
  }

  # Conectar este serviço ao environment do projeto
  environment_id = render_project.project.environments["production"].id
}

# Caso queira associar o Postgres privado ao web service, o provider pode realizar attachments/links.
# Consulte a documentação do provider render-oss/render para detalhes sobre attachment/connection entre serviços.