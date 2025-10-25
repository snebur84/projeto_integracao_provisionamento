```markdown
# infra/terraform/render

Nota: este diretório usa o provider oficial do Render no registry: `render/render`.

O arquivo provider.tf já está configurado para usar:
- source = "render/render"
- versão mínima: ">= 0.10.0" (ajuste conforme desejar)

Antes de rodar:
1. Verifique a versão do provider no Terraform Registry e ajuste o `version` em provider.tf se quiser travar uma versão específica.
2. Garanta que o secret `RENDER_API_KEY` esteja criado no GitHub. O workflow injeta esse valor como `TF_VAR_render_api_key`.
3. Revise `variables.tf`, `main.tf` e `terraform.tfvars.example` conforme necessário.
4. Execute o workflow manualmente (Actions → Terraform Apply (Render) → Run workflow) ou rode `terraform init && terraform apply` localmente em `infra/terraform/render`.

Se qualquer atributo de recurso do provider (`render_service`, `persistent_disk`, `internal_hostname`, etc.) falhar no `terraform plan`, abra a documentação do provider `render/render` e ajuste os nomes dos atributos (algumas chaves podem ter nomes ligeiramente diferentes dependendo da versão do provider).
```