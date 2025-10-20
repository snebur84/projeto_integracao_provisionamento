# Projeto: Integração de Provisionamento

Este repositório contém a aplicação Django usada para gerar arquivos de provisionamento (XML / CFG) para aparelhos, com templates armazenados em MongoDB e dados de dispositivo/perfil em MySQL. [...]

Sumário rápido
- Deploy local (desenvolvimento / testes)
- Deploy na AWS (EC2 + SSM, com opção Terraform via infra/terraform)
- Deploy no GCP (Compute Engine + Cloud SQL / opções para MongoDB)
- Resumo da interface de gestão (management UI)
- API de download de configuração (/api/download-xml/)
- Como testar a API com Postman
- Troubleshooting e verificações úteis

----------------------------------------------------------------
1) Deploy local (rápido)
Pré-requisitos
- Python 3.10+ (ou conforme requirements.txt)
- MySQL local acessível
- MongoDB local acessível
- Git
- (Opcional) Docker e docker-compose para execução em container

Observação importante sobre o script de provisionamento local
- Existe um script que prepara e controla todo o deploy localmente: `scripts/provision_ubuntu_full.sh`.
- Antes de executar, siga os passos abaixo para garantir permissões corretas.

Passos (recomendado)
1. Clone o repo e entre no diretório da app:
   ```bash
   git clone https://github.com/snebur84/projeto_integracao_provisionamento.git
   cd projeto_integracao_provisionamento
   ```

2. Adicione sua chave pública SSH / verifique se você tem acesso local se necessário (opcional).

3. Adicione o seu usuário ao grupo docker (se for usar Docker localmente)
   - Adicionar o usuário atual ao grupo `docker`:
     ```bash
     sudo usermod -aG docker $USER
     ```
   - Depois desse comando é necessário fazer logoff e login (ou reiniciar a sessão) para que a nova permissão de grupo seja aplicada.

4. Garanta permissão de execução no script de provisionamento:
   ```bash
   chmod +x scripts/provision_ubuntu_full.sh
   ```

5. Execute o script de provisionamento local:
   - Recomenda-se executar com sudo para que o script consiga instalar pacotes e configurar o sistema:
     ```bash
     sudo bash scripts/provision_ubuntu_full.sh
     ```
   - O script irá:
     - atualizar o servidor,
     - gerar/criar variáveis e escrever o arquivo `.env` (se necessário),
     - instalar dependências (virtualenv, pip packages),
     - aplicar migrations e `collectstatic`,
     - configurar serviços (nginx, systemd/gunicorn) conforme o fluxo local,
     - no final, solicitará interativamente o usuário e senha do django-admin para a criação do superuser.

6. Após término do script:
   - Se o script configurou systemd/gunicorn/nginx, verifique status dos serviços:
     ```bash
     sudo systemctl status provision
     sudo systemctl status nginx
     sudo journalctl -u provision -n 200
     ```
   - Acesse localmente:
     - Login: http://<ip do servidor>
     - Admin: http://<ip do servidor>/admin
     - API: http://<ip do servidor>/api/

Observações adicionais
- Se você preferir não instalar pacotes no host, mantenha e use `docker-compose.yml` (desenvolvimento em container). O script `scripts/provision_ubuntu_full.sh` é a opção "instala no host".
- Nunca comite arquivos `.env` com segredos no repositório. Use `.env.example` como referência.

----------------------------------------------------------------
2) Deploy na AWS (resumo / fluxo usado neste projeto)
Opções suportadas
- Fluxo recomendado (automático): GitHub Actions workflow `.github/workflows/deploy-terraform-ec2.yml`
  - Detecta uma EC2 existente por tag (Project = environment) ou executa Terraform (infra/terraform) para criar infra.
  - Faz upload do script `scripts/provision_ubuntu_ec2.sh` para um bucket S3 de staging.
  - Gera (se necessário) secrets dinâmicos no SSM Parameter Store (SECRET_KEY, DB_PASSWORD, PROVISION_API_KEY) como SecureString.
  - Invoca SSM RunCommand para baixar e executar o script na instância (o script instala dependências, configura venv, aplica migrations, cria systemd unit e configura nginx).

Requisitos da instância EC2 (quando reutilizada)
- Amazon SSM Agent instalado e registrado em Systems Manager.
- Instance Profile (IAM Role) com política `AmazonSSMManagedInstanceCore`.
- Permissão `ssm:GetParameter` (ou política que permita leitura dos parâmetros SSM usados).
- Tag `Project = <environment>` (workflow usa isso para detectar instância).
- Segurança de rede: portas relevantes (HTTP/HTTPS) no Security Group.

Fluxo via GitHub Actions (resumido)
- Workflow identifica EC2 ou executa Terraform.
- Faz upload do script para S3.
- Gera parâmetros SecureString no SSM (opcional).
- Executa SSM RunCommand para aplicar provisioning na instância.

Notas importantes
- Prefira GitHub OIDC para o Actions assumir role em AWS em vez de armazenar chaves de longa duração.
- Sempre crie políticas IAM com princípio do menor privilégio.
- Use S3 + KMS para arquivos transitados e SSM Parameter Store (SecureString) ou Secrets Manager para segredos.

----------------------------------------------------------------
2.b) Deploy no GCP (Compute Engine + Cloud SQL / opções MongoDB)

Resumo de opções
- Opção gerenciável (recomendada):
  - Cloud SQL (MySQL) para o banco relacional.
  - MongoDB: usar MongoDB Atlas (gerenciado) ou criar uma VM Compute Engine dedicada com MongoDB.
  - Compute Engine (VM) para rodar a aplicação (systemd/gunicorn + nginx) ou usar GKE (Kubernetes) se preferir orquestração.
  - Cloud Storage (GCS) para artefatos de staging (scripts, uploads).
  - Secret Manager para segredos (ou usar conexões do Cloud SQL + Secret Manager).
- Opção containerizada:
  - BuildImage com Cloud Build e deploy no GCE (instance) ou GKE.
  - Use Cloud Run apenas se sua aplicação for adaptada para execução stateless como serviço HTTP (requer adaptar o acesso ao DB).

Componentes recomendados
- Compute Engine:
  - VM Ubuntu com startup script que baixa e executa `scripts/provision_ubuntu_full.sh` adaptado para GCP, ou use um script específico `scripts/provision_gcp.sh`.
  - Garanta Firewall (HTTP/HTTPS) e contas de serviço com papéis adequados.
- Cloud SQL (MySQL):
  - Crie uma instância MySQL.
  - Use o Cloud SQL Proxy (local ou via sidecar/container) ou autorização por rede privada (VPC connector) para conectar o app à Cloud SQL.
- MongoDB:
  - Recomendado: MongoDB Atlas (instância gerenciada). Alternativa: instalar MongoDB em uma VM do Compute Engine (requer gerência de backups, HA).
- Secret Manager:
  - Armazene SECRET_KEY, PROVISION_API_KEY, e credenciais DB (Cloud SQL password) no Secret Manager.
- Cloud Storage:
  - Bucket para staging de scripts/artefatos (equivalente ao S3 usado pela versão AWS).

Passos básicos (exemplo manual)
1. Criar projeto GCP e ativar APIs:
   - Compute Engine, Cloud SQL Admin, Secret Manager, Cloud Storage, IAM.
2. Provisionar Cloud SQL (MySQL) e criar DB/usuário.
3. Provisionar MongoDB (Atlas) ou preparar uma VM com MongoDB.
4. Criar uma VM Compute Engine (Ubuntu) com um Service Account que tenha:
   - roles/cloudsql.client (para conectar ao Cloud SQL)
   - roles/secretmanager.secretAccessor (para ler segredos)
   - roles/storage.objectViewer (se precisar baixar scripts do bucket)
5. Fazer upload do script de provisionamento para um bucket GCS, ou provisionar via SSH/Cloud Build.
6. Conectar na VM e executar o script de provisionamento adaptado:
   - Ajuste `.env` com variáveis apontando para Cloud SQL e MongoDB (ou use Secret Manager para injetar).
7. Verificar serviços: systemd/gunicorn/nginx e logs.

Fluxo via GitHub Actions (sugestão)
- Use Workload Identity Federation (recomendado) para permitir que o workflow assuma um Service Account do GCP (evita armazenar chave JSON em Secrets).
- Alternativa: armazene uma chave de Service Account (JSON) no GitHub Secret `GCP_SA_KEY` e use `google-github-actions/auth` no workflow.
- Etapas típicas:
  1. Autenticar no GCP (OIDC ou SA key).
  2. Executar Terraform (se houver infra como código para GCP).
  3. Fazer upload de script para GCS.
  4. Usar `gcloud compute ssh` ou `gcloud compute ssh --command` (ou invocar Cloud Build) para executar o script na VM.

Observações e boas práticas GCP
- Use VPC privada para comunicação entre app e Cloud SQL.
- Use Secret Manager e atribua permissões estritas aos Service Accounts.
- Prefira Workload Identity Federation para GitHub Actions.

----------------------------------------------------------------
3) Resumo da interface de gestão (Management UI)
- A aplicação fornece uma interface administrativa (Django Admin) para:
  - Gerenciar Devices (dispositivos): registrar identifiers e atributos do aparelho.
  - Gerenciar Profiles (perfis): definir parâmetros SIP/linha/voip e demais campos usados no template.
  - Gerenciar Templates: armazenar templates de configuração (XML/CFG) no MongoDB com metadados (modelo, extensão).
  - Visualizar e editar templates atribuídos a perfis.
- Papel da interface: permitir operadores/criadores de perfil inserir/editar templates e vincular perfis a dispositivos para que a API de provisionamento gere o arquivo apropriado.

----------------------------------------------------------------
4) API de download de configuração
Endpoint principal
- GET `/api/download-xml/` (ponto de entrada principal)  
- Também pode aceitar um "filename" na URL, por exemplo:
  `GET /api/download-xml/config.cfg`

Comportamento
- A rota retorna um arquivo de configuração (XML ou CFG) gerado a partir do template armazenado no Mongo e dados (device/profile) vindo do MySQL.
- Se `filename` terminar em `.cfg` a response será `text/plain` (ext = cfg); caso contrário retorna `application/xml` (ext = xml).
- Placeholders do tipo `%%nome%%` no template são substituídos por valores vindos do contexto (dados do device/profile). Booleanos são convertidos para `1`/`0`.
- Autenticação: suporte a Bearer token (`Authorization: Bearer <token>`) ou `X-API-KEY` header conforme sua configuração.

Cabeçalhos importantes
- `Authorization: Bearer <ACCESS_TOKEN>`  (ou) `X-API-KEY: <KEY>`
- `User-Agent: Fabricante Modelo Versao Mac` (alguns provisionadores esperam User-Agent específico)

Códigos de status esperados
- `200 OK` — arquivo retornado
- `403 Forbidden` — falta de permissão / erro de render
- `404 Not Found` — template ou device não encontrado
- `500` — erro do servidor (ver logs)

----------------------------------------------------------------
5) Como testar a API com Postman
Preparar
- Abra o Postman e crie uma nova Collection (ex: Provisionamento).
- Crie uma nova requisição GET.

Configuração da requisição
- URL:
  - Local: `http://<ip do servidor>/api/download-xml/`
  - Remoto (prod): `https://your.domain.tld/api/download-xml/config.xml`  (ou sem filename)
- Headers:
  - `Authorization: Bearer <TOKEN>`  (ou) `X-API-KEY: <KEY>`
  - `User-Agent: Fabricante Modelo Versao Mac`

Exemplo de fluxo no Postman
1. Defina método `GET` e URL.
2. No tab "Headers" adicione `Authorization` e `User-Agent`.
3. Envie a requisição.
4. Avalie a resposta:
   - Verifique HTTP `200` e o body retornado tem a configuração (XML/CFG).
   - Confirme que placeholders `%%sipserver%%` (e similares) foram substituídos por valores reais.
   - Verifique `Content-Type`: `application/xml; charset=utf-8` para XML ou `text/plain` para cfg.

Testes adicionais
- Forçar `.cfg`:
  `GET https://your.domain.tld/api/download-xml/config.cfg`
- Sem filename (usa XML por padrão):
  `GET https://your.domain.tld/api/download-xml/`

----------------------------------------------------------------
6) Troubleshooting rápido
- "NameError: get_mongo_client is not defined" — verifique import em `app/provision/api/views.py` e que `api.utils.mongo.get_mongo_client` está disponível.
- Templates com placeholders não substituídos: confirme que o código aplica a substituição `%%nome%%` após render e que context contém as chaves corretas (lowercase).
- Erro ao criar DB: confirme variáveis MySQL no `.env` e permissões do usuário.
- SSM / deploy AWS: se o RunCommand não chegar ao host, verifique se a instância tem SSM Agent ativo e aparece em Systems Manager → Managed Instances.
- GCP: se a VM não consegue conectar ao Cloud SQL, verifique Cloud SQL Proxy, VPC e permissões do service account.

----------------------------------------------------------------
7) Variáveis / Secrets recomendados para o repositório
A seguir as variáveis/secrets recomendadas a criar no GitHub (Settings → Secrets & variables → Actions). Separei por destino (AWS / GCP) e comuns.

Comuns (necessárias independentemente do provedor)
- SECRET_KEY — Django SECRET_KEY (string segura)
- PROVISION_API_KEY — chave usada pela API (ou nome alternativo conforme implementação)
- DJANGO_ALLOWED_HOSTS — hosts permitidos (ex: your.domain.tld)
- ENVIRONMENT — ex: prod / staging
- DB_NAME — nome do banco MySQL usado pela aplicação (quando não usar Cloud SQL URL)
- DB_USER — usuário do MySQL
- DB_PASSWORD — senha do MySQL (se não for armazenada em Secret Manager)
- MONGO_URI ou MONGO_ATLAS_URI — string de conexão do MongoDB (ex: mongodb+srv://...)
- SENTRY_DSN (opcional) — se usar Sentry

AWS (se for usar o fluxo AWS)
- AWS_ACCESS_KEY_ID — *apenas se não usar OIDC* (evite quando possível)
- AWS_SECRET_ACCESS_KEY — *apenas se não usar OIDC*
- AWS_REGION — ex: us-east-1
- S3_BUCKET — bucket de staging para scripts/artefatos usados pelo workflow
- SSM_PREFIX (opcional) — prefixo nos parâmetros SSM (ex: /provisioning/prod)
- SSM_SECRET_KEY_NAME — nome do parametro SSM para SECRET_KEY (se for usar SSM)
- TF_VAR_tfstate_bucket — bucket S3 para o state do Terraform (se usar Terraform)
- TF_VAR_tfstate_lock_table — nome da tabela DynamoDB para lock (Terraform)

GCP (se for usar o fluxo GCP)
- GCP_PROJECT — ID do projeto GCP
- GCP_REGION — região (ex: us-central1)
- GCP_ZONE — zona (ex: us-central1-a) (opcional)
- GCP_SA_KEY — chave JSON do Service Account (se NÃO estiver usando Workload Identity Federation). JSON inteiro como secret.
- GCS_BUCKET — bucket para staging (equivalente a S3_BUCKET)
- CLOUD_SQL_CONNECTION_NAME — connection name do Cloud SQL (ex: project:region:instance)
- CLOUD_SQL_USER — usuário do Cloud SQL (se for injetar via secret)
- CLOUD_SQL_PASSWORD — senha do Cloud SQL (ou armazenar em Secret Manager)
- SECRET_MANAGER_PREFIX (opcional) — prefixo/key para os segredos no Secret Manager
- MONGO_ATLAS_URI — string de conexão do MongoDB Atlas (se usar)

Observações sobre armazenamento de segredos
- AWS: prefira SSM Parameter Store (SecureString) ou AWS Secrets Manager; configure a EC2 para ter permissão de leitura (via Instance Profile).
- GCP: prefira Secret Manager; atribua papel `secretmanager.secretAccessor` ao Service Account usado pela VM.
- GitHub Actions: prefira OIDC (Workload Identity Federation) para evitar armazenar chaves long-lived. Documente o processo de configuração (roles / trust relationships).

----------------------------------------------------------------
8) Exemplos rápidos de integração com GitHub Actions

A) AWS (esquema resumido)
- Autenticar (preferência: OIDC assume-role no AWS).
- Se necessário, rodar Terraform (infra/terraform).
- Upload do `scripts/provision_ubuntu_ec2.sh` ao S3 (usando `aws s3 cp`).
- Call ao SSM RunCommand (aws ssm send-command) para executar script na instância.

Secrets GitHub necessários (mínimo quando usar OIDC):
- AWS_REGION
- S3_BUCKET
- (se não usar OIDC: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

B) GCP (esquema resumido)
- Autenticar: `google-github-actions/auth` com Workload Identity (recomendado) ou `GCP_SA_KEY`.
- (Opcional) Executar Terraform para criar VM/Cloud SQL.
- Upload do script para GCS (`gsutil cp`).
- Invocar `gcloud compute ssh` para executar o script na VM, ou usar Cloud Build para orquestrar deploy.

Secrets GitHub necessários (mínimo quando usar OIDC):
- GCP_PROJECT
- GCS_BUCKET
- (se não usar OIDC: GCP_SA_KEY)

----------------------------------------------------------------
9) Boas práticas e segurança
- Nunca commit `.env` com segredos. Use Secret Manager/SSM/Secrets Manager.
- Prefira GitHub OIDC + assume-role (AWS) / Workload Identity Federation (GCP) ao invés de long-lived keys.
- Mantenha o state do Terraform em backend remoto (S3/GCS) com locking (DynamoDB / equivalentos).
- Restrinja quem pode executar workflows que rodam Terraform (branch protections, approvals).
- Use KMS para criptografar segredos e restringir a leitura apenas a service accounts/roles necessários.

----------------------------------------------------------------
10) Contatos / próximos passos
Se precisar que eu:
- gere o Postman collection export (JSON) pronto,
- atualize exemplos de `.env`,
- abra PR com melhorias na documentação,
- adapte `scripts/provision_ubuntu_full.sh` para suportar startup script GCP,
avise e eu faço os artefatos.

Obrigado — bom deploy!
