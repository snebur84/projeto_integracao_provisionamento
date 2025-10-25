```markdown
# Render Terraform (adaptado para render-oss/render)

O main.tf foi atualizado para usar os resource types detectados no provider `render-oss/render`:
- render_project
- render_private_service (usado para MySQL e Mongo)
- render_web_service (usado para a app Django)

O que foi feito
- Criei um render_project opcional para agrupar serviços.
- Criei 2 render_private_service para MySQL e Mongo (imagens oficiais).
- Criei um render_web_service para a app Django (build do repo).
- Passei variáveis de ambiente para a app incluindo hostnames internos das services.

Atenção (possíveis ajustes)
- Alguns atributos (por exemplo `persistent_disk`, `internal_hostname`, `default_domain`, `repo`, `build_command`) podem ter nomes/detalhes diferentes na versão do provider que você tem instalada. Se terraform plan/reportar erros de "Unknown attribute" ou "Unsupported block", cole aqui o trecho do erro que eu corrijo imediatamente.
- Se ocorrer um ciclo de dependência (env_group vs service criado), a alternativa é usar render_env_group + render_env_group_link ou mover variáveis sensíveis para env groups. Eu deixei tudo direto no bloco `env` da web_service para simplificar o fluxo inicial.
- Garanta que a conta Render tem suporte a Persistent Disk e Private/Internal services no plano da conta.

Passos para testar localmente (recomendado)
1. Ajuste variáveis sensíveis via TF_VAR_* ou terraform.tfvars (não comite).
   export TF_VAR_render_api_key="<RENDER_API_KEY>"
   export TF_VAR_django_secret_key="<DJANGO_SECRET_KEY>"
   export TF_VAR_mysql_root_password="<MYSQL_ROOT_PASSWORD>"
   export TF_VAR_mysql_password="<MYSQL_PASSWORD>"
   export TF_VAR_mongodb_root_password="<MONGODB_ROOT_PASSWORD>"
2. No diretório infra/terraform/render:
   terraform init -upgrade
   terraform plan -out=tfplan
   terraform apply -input=false -auto-approve tfplan
3. Se houver erros, cole os trechos aqui e eu corrijo.

Se quiser, eu já adapto os blocos caso o provider reclame de atributos específicos (por exemplo se o provider exigir um bloco "build" em vez de "repo/branch"), cole o erro e eu atualizo o main.tf imediatamente.
```