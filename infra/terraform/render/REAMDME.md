```markdown
# infra/terraform/render — adaptado ao provider render-oss/render

Resumo:
- Este conjunto de arquivos cria:
  - um `render_project` com um ambiente (map de objetos)
  - 2 `render_private_service` (MySQL e Mongo) usando `runtime_source.image`
  - 1 `render_web_service` (Django app) usando `runtime_source.docker` (build via Dockerfile no repo)
  - `env_vars` são configuradas diretamente como map de objetos `{ value = ... }` conforme schema do provider

Importante:
- O provider exige `runtime_source` como objeto com sub-blocos `docker`, `image` ou `native_runtime`.
- `render_project.environments` é um map de objects — use a mesma estrutura no `variable "project_environments"`.
- A associação entre serviços e o ambiente do projeto é feita via `environment_id = render_project.project.environments["<key>"].id`.

Como testar localmente:
1. Exporte a API key:
   export TF_VAR_render_api_key="<your_render_api_key>"
2. (Opcional) export TF_VAR_render_owner_id if needed
3. Ajuste os secrets/variáveis sensíveis via TF_VAR_* localmente (não comite)
4. Rode:
   cd infra/terraform/render
   terraform init -upgrade
   terraform validate
   terraform plan -out=tfplan
   terraform apply -input=false -auto-approve tfplan

Se houver erros de "unknown attribute" ou "unsupported block", cole o trecho exato do erro aqui e eu ajusto os blocos conforme a versão do provider instalado no runner.
```