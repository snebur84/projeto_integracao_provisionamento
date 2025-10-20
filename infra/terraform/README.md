# Infra / Terraform — orientações rápidas

Este diretório contém a infraestrutura como código usada pelo projeto. Mantê-lo no repositório é útil para reproduzir, auditar e evoluir a infraestrutura (EC2, IAM, S3, etc).

Resumo
- Use este código para criar/atualizar a infra via Terraform.
- O workflow Actions (`.github/workflows/deploy-terraform-ec2.yml`) pode executar o Terraform automaticamente.
- Recomendações de segurança e operação estão abaixo.

Antes de rodar (recomendações)
1. Backend remoto (recomendado)
   - Configure um bucket S3 e uma tabela DynamoDB para backend/lock.
   - Defina as variáveis `TF_VAR_tfstate_bucket` e `TF_VAR_tfstate_lock_table` ou configure `backend.tf`.
   - Não comite credenciais no repo.

2. Credenciais/Permissões
   - Prefira usar GitHub OIDC to assume-role para Actions.
   - Se usar chaves, adicione `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` nos Secrets do repositório.
   - Conta/role usada pelo Actions precisa de permissões necessárias ao Terraform (ec2, iam, s3, dynamodb, ssm).

Comandos úteis (local / CI)
- Inicializar e validar:
  terraform init
  terraform validate

- Ver o state atual:
  terraform state list

- Ver outputs:
  terraform output -json

- Aplicar mudanças:
  terraform plan -out=tfplan
  terraform apply -auto-approve tfplan

Importar uma instância EC2 existente (se a instância foi criada manualmente)
1. Verifique o resource block em `infra/terraform/main.tf` que corresponde à instância (ex.: `aws_instance.provision`).
2. Rode (local/CI):
   terraform init
   terraform import aws_instance.provision i-0123456789abcdef0
3. Rode `terraform plan` para ver se a configuração do TF bate com a instância real e ajuste o codigo se necessário.

Notas sobre o workflow de CI/CD
- O workflow `deploy-terraform-ec2.yml` suporta dois caminhos:
  1. Detectar EC2 existente (por tag) e pular Terraform.
  2. Executar Terraform para criar infra (quando nada for encontrado).
- Se você preferir não permitir que Actions crie infra, defina as variáveis/secrets `SSM_INSTANCE_ID` e `S3_BUCKET` e ajuste o workflow para pular o job Terraform.

Segurança e boas práticas
- Armazene o estado remoto em S3 com criptografia e DynamoDB para locking.
- Restrinja quem pode executar workflows que correm Terraform (branch protections, environments approvals).
- Use KMS para SSM SecureString, e restrinja a leitura dos parâmetros SSM apenas ao Instance Profile da EC2.
- Evite enviar `.env` inteiros via S3; prefira SSM Parameter Store (SecureString).

Manutenção e limpeza
- Arquive workflows antigos ao invés de deletar (ex.: `.github/workflows/disabled/`) para manter histórico.
- Se decidir remover `infra/terraform`, primeiro:
  - exporte os outputs importantes (instance_id, bucket),
  - import a instância no Terraform state ou documente que a infra será gerenciada fora do repo,
  - remova o diretório via PR e atualize os workflows para usar secrets estáticos.

Seção: checklist pós-deploy (rápida)
- [ ] `terraform output` e valores exportados (instance_id, staging_bucket)
- [ ] EC2 aparece no Systems Manager (SSM)
- [ ] instance profile tem `AmazonSSMManagedInstanceCore` e permissão `ssm:GetParameter` para SSM params
- [ ] TF state bucket + DynamoDB lock configurados e acessíveis
- [ ] Workflows GitHub atualizados para usar OIDC ou credenciais seguras

Problemas comuns e resolução rápida
- "Instance not found" → verifique tags / região / permissões EC2 DescribeInstances
- "Terraform state mismatch" → rode `terraform import` para sincronizar
- "SSM command fails" → verifique role da instância (SSM) e logs em Systems Manager > Run Command