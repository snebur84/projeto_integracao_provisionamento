# Projeto de Provisionamento

Este repositório implementa um sistema de provisionamento de dispositivos com:
- Modelagem mestre/detalhe: DeviceProfile (perfil) ⇢ DeviceConfig (dispositivo) (1→N).
- Registro de tentativas de provisionamento em um model separado: Provisioning.
- API de provisionamento (download de configuração) com suporte a OAuth2 (django-oauth-toolkit) e fallback por API key.
- Painel administrativo, views CRUD e telas mestre/detalhe (profile + inline devices).

Este README resume como configurar, executar e testar o sistema após as alterações recentes (integração OAuth2, models e telas mestre/detalhe).

Sumário
- Requisitos
- Instalação rápida
- Variáveis de ambiente importantes
- Migrations e bancos
- OAuth2 (django-oauth-toolkit) — instalação e uso
- Endpoints principais e testes (curl)
- Interface web (mestre/detalhe)
- Migração de dados existentes
- Segurança e boas práticas
- Troubleshooting

Requisitos
- Python 3.8+
- Django (versão do projeto)
- MySQL (ou outro banco configurado)
- MongoDB (opcional, usado para templates)
- poetry ou pip para dependências

Instalação rápida (development)
1. Clone:
   git clone https://github.com/snebur84/projeto_integracao_provisionamento.git
   cd projeto_integracao_provisionamento/app/provision

2. Crie e ative seu virtualenv e instale dependências. Exemplo com poetry:
   poetry install

   Caso não use poetry, instale as dependências listadas no requirements.

3. Instale django-oauth-toolkit (necessário para OAuth2):
   poetry add django-oauth-toolkit
   # ou
   pip install django-oauth-toolkit

4. Configure variáveis de ambiente (ver seção abaixo).

5. Gere e aplique migrations:
   python manage.py makemigrations
   python manage.py migrate

6. Crie superuser (administrador Django):
   python manage.py createsuperuser

7. Execute o servidor:
   python manage.py runserver

Variáveis de ambiente importantes
- DJANGO_SECRET_KEY — secret do Django.
- DJANGO_DEBUG — 0 ou 1.
- DJANGO_ALLOWED_HOSTS — hosts permitidos (comma-separated).
- MYSQL_* ou DJANGO_DB_* — credenciais do banco relacional.
- MONGODB_* — configuração do MongoDB (se usado).
- PROVISION_API_KEY — chave utilizada como fallback para dispositivos simples (opcional).
- OAUTH_ACCESS_TOKEN_EXPIRE, OAUTH_REFRESH_TOKEN_EXPIRE — timeouts de tokens OAuth.
- EMAIL_* — servidor de e-mail para password reset.

Models principais (resumo)
- DeviceProfile: perfil do dispositivo (sip_server, port_server, protocol_type, template_ref, metadata, timestamps).
- DeviceConfig: dispositivo (profile FK, identifier, mac_address, user_register, passwd_register, display_name, counters e IPs).
- Provisioning: registro por tentativa (vendor, model, version, public_ip, private_ip, status, template_ref, user_agent, metadata, timestamps).

Master/Detail (UI)
- Tela mestre/detalhe: criar/editar DeviceProfile e, na mesma tela, criar/editar DeviceConfig associados via inline formset.
  - URL: /profiles/ (list), /profiles/create/ (novo), /profiles/<pk>/edit/ (editar).
- Dispositivos também têm CRUD próprio:
  - /devices/, /devices/create/, /devices/<pk>/, /devices/<pk>/edit/

OAuth2 (django-oauth-toolkit) — instalação e uso
1. Instale a biblioteca (veja acima) e aplique migrations:
   python manage.py migrate

2. Crie um OAuth2 Application (client).
   - Opção A (admin): Acesse /admin/ → Applications → Add application e defina:
     - name, client type (confidential/public), authorization grant type (client credentials para M2M ou authorization code para usuários).
     - redirect URIs se usar authorization code.
   - Opção B (linha de comando): use o management command criado:
     python manage.py create_oauth_application --name provision-m2m --client-type confidential --grant-type client-credentials --scopes "provision read"
     O comando imprime client_id e client_secret.

3. Obter token client_credentials (exemplo curl):
   curl -X POST -u "<client_id>:<client_secret>" \
     -d "grant_type=client_credentials&scope=provision" \
     https://<host>/o/token/

4. Usar token para chamar endpoints protegidos:
   curl -H "Authorization: Bearer <access_token>" https://<host>/api/whoami/
   ou para download de configuração:
   curl -H "Authorization: Bearer <access_token>" https://<host>/api/download-xml/

Fallback para dispositivos simples
- O endpoint de download (download_config) tenta autenticar por OAuth2 (exigindo scope `provision` ou `read`). Se não houver token válido, faz fallback para PROVISION_API_KEY (se configurado), preservando compatibilidade com dispositivos que não suportam OAuth.
- Recomendação: migrar dispositivos/gateways para client_credentials e remover o fallback quando todos os clientes estiverem portados.

Documentação OpenAPI / Swagger
- A UI swagger está disponível em /api/docs/ e a schema em /api/schema/.
- O drf-spectacular foi configurado com um security scheme OAuth2 (client credentials) — use o fluxo manualmente para obter token e cole no campo de autorização da UI.

Endpoints principais (resumo)
- /api/download-xml/(<filename>/) — endpoint de provisionamento principal (GET). Espera User-Agent no formato: "vendor model version <mac|identifier>".
- /api/whoami/ — exemplo de endpoint protegido por OAuth2 (scope read).
- /o/ — endpoints do django-oauth-toolkit: /o/token/, /o/authorize/, /o/revoke_token/, /o/introspect/, /o/applications/ (admin UI e APIs).
- Admin: /admin/ — gerenciar models e Applications.

Testes e validação (rápido)
- Testar token issuance e acesso:
  1) Criar Application (client credentials).
  2) curl para /o/token/ (obter access_token).
  3) curl com Authorization Bearer para /api/whoami/ e /api/download-xml/.
- Testar fallback:
  - Configure PROVISION_API_KEY no env e chame /api/download-xml/ informando X-API-KEY header.

Migração de dados existentes
- Se já houver dados em DeviceConfig e você quer extrair perfis:
  1) Escreva uma data migration que:
     - Crie perfis padrão (ou perfis a partir de valores comuns).
     - Atribua DeviceConfig.profile = perfil correspondente.
  2) Em produção, teste em staging antes de migrar.
- Se quiser preservar histórico de attempts_provisioning em registros Provisioning, gere um script/migration que crie registros Provisioning a partir do estado atual (opcional).

Boas práticas de segurança / operações
- Armazene client_secrets e PROVISION_API_KEY em secret manager (não no código).
- Habilite HTTPS em produção e configure SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE/HSTS.
- Rotacione client_secrets e API keys periodicamente.
- Evite logar senhas/segredos; se for necessário armazenar tokens ou credenciais, proteja com KMS.
- Para proteção contra brute-force em autenticação, considere tools como django-axes.

Ajustes sugeridos / trabalho pendente (para chegar a "pronto em produção")
- Garantir que todos os endpoints sensíveis sejam protegidos por OAuth2 e scopes apropriados (ainda há endpoints com proteção exemplar).
- Revisar e remover fallback PROVISION_API_KEY quando migrar todos os dispositivos.
- Criar testes de integração cobrindo issuance de token, introspecção, e autorização por scopes.
- Adicionar rotinas de monitoramento e auditoria de tokens emitidos/revocados.

Troubleshooting rápido
- Erro 500/ImportError sobre oauth2_provider: instale django-oauth-toolkit e rode migrate.
- Rotas /api/whoami/ não encontradas: confirme que `api.urls` está incluído em provision/urls.py e que app `api` está em INSTALLED_APPS.
- Erro em admin Application: verifique migrações e privilégios do usuário admin.

Contribuição
- Abra issues/PRs com melhorias, correções ou perguntas.
- Se for proposta de alteração em produção (rotas de autenticação, remoção de fallback), faça em branch separado e teste em staging.

Contato
- Desenvolvedor/owner: @snebur84 (GitHub).

-----
Notas finais
Este README cobre o estado atual após as alterações recentes (modelagem mestre/detalhe, Provisioning separado e integração inicial com OAuth2). Se quiser, eu:
- gero um exemplo de script de migração de dados para popular DeviceProfile a partir de DeviceConfig existentes;
- adiciono exemplos de testes (pytest) para OAuth2 flows e endpoints;
- removo o fallback PROVISION_API_KEY e atualizo a documentação para exigir somente OAuth2.
Qual opção prefere que eu gere a seguir?