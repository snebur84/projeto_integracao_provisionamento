# Projeto: Integração de Provisionamento

Este repositório contém a aplicação Django usada para gerar arquivos de provisionamento (XML / CFG) para aparelhos, com templates armazenados em MongoDB e dados de dispositivo/perfil em MySQL. Também há scripts para deploy local e infração mínima para deploy em AWS (EC2 + SSM), além de workflows GitHub Actions para automatizar o provisionamento.

Sumário rápido
- Deploy local (desenvolvimento / testes)
- Deploy na AWS (EC2 + SSM, com opção Terraform via infra/terraform)
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
   - Depois desse comando é necessário fazer logoff e login (ou reiniciar a sessão) para que a nova permissão de grupo seja aplicada. Execute logoff/login antes de prosseguir com o passo de execução do script.

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
- Se você preferir não instalar pacotes no host, mantenha e use `docker-compose.yml` (desenvolvimento em container). O script `scripts/provision_ubuntu_full.sh` é a opção "instala no host" que facilita testes de integração em uma VM Ubuntu.
- Nunca comite arquivos `.env` com segredos no repositório. Use `.env.example` como referência.

----------------------------------------------------------------
2) Deploy na AWS (resumo / fluxo usado neste projeto)
Opções suportadas
- Fluxo recomendado (automático): GitHub Actions workflow `.github/workflows/deploy-terraform-ec2.yml`
  - Detecta uma EC2 existente por tag (Project = environment) ou executa Terraform (infra/terraform) para criar infra.
  - Faz upload do script `scripts/provision_ubuntu_ec2.sh` para um bucket S3 de staging.
  - Gera (se necessário) secrets dinâmicos no SSM Parameter Store (SECRET_KEY, DB_PASSWORD, PROVISION_API_KEY) como SecureString.
  - Invoca SSM RunCommand para baixar e executar o script na instância (o script instala dependências, configura venv, aplica migrations, cria systemd unit e configura nginx).

Pré-requisitos para o workflow funcionar
- GitHub Secrets/Variables configurados conforme descrito em `infra/README.md` e no workflow (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, etc).
- EC2 (quando reutilizada) deve:
  - ter Amazon SSM Agent instalado e registrada em Systems Manager
  - ter um Instance Profile com política `AmazonSSMManagedInstanceCore` e permissão `ssm:GetParameter` para ler parâmetros
  - estar na mesma região do workflow
  - ter tag `Project = <environment>` (workflow usa isso para detectar instância)

Como iniciar o deploy via GitHub
- UI: Actions → deploy-terraform-ec2 → Run workflow → input `environment` (ex: `prod`)
- CLI (gh):
  ```bash
  gh workflow run deploy-terraform-ec2.yml --field environment=prod
  ```

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

----------------------------------------------------------------
7) Boas práticas e segurança
- Nunca commit `.env` com segredos. Use SSM Parameter Store (SecureString) ou Secrets Manager para armazenar segredos em produção.
- Prefira GitHub OIDC + assume-role em Actions em vez de long-lived AWS keys.
- Mantenha o state do Terraform em um backend S3 com DynamoDB locking.
- Restrinja o acesso SSH (ou prefira Session Manager/SSM).

----------------------------------------------------------------
8) Contatos / próximos passos
Se precisar que eu:
- gere o Postman collection export (JSON) pronto,
- atualize exemplos de `.env`,
- abra PR com melhorias na documentação,
avise e eu faço os artefatos.

Obrigado — bom deploy!
