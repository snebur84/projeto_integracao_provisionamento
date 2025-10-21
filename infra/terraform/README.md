# Infra / Terraform — Multi-Cloud Infrastructure

Este diretório contém a infraestrutura como código para deployments em AWS e GCP. A estrutura foi reorganizada para suportar múltiplos provedores de nuvem de forma concorrente e independente.

## Estrutura do Diretório

```
infra/terraform/
├── aws/                    # Configurações específicas da AWS
│   ├── main.tf            # Recursos AWS (S3, EC2, etc.)
│   ├── providers.tf       # Provider AWS
│   ├── variables.tf       # Variáveis AWS
│   ├── outputs.tf         # Outputs AWS
│   ├── instances.tf       # Configurações de instâncias EC2
│   ├── version.tf         # Versão do Terraform e providers
│   ├── modules/           # Módulos AWS (VPC, ECS, ECR)
│   ├── templates/         # Templates para user_data, etc.
│   └── backend.hcl.example # Exemplo de configuração do backend S3
├── gcp/                    # Configurações específicas do GCP
│   ├── gcp-provider.tf    # Provider GCP
│   ├── gcp-compute.tf     # Recursos GCP (Compute Engine)
│   ├── variables.tf       # Variáveis GCP
│   └── backend.hcl.example # Exemplo de configuração do backend GCS
├── bootstrap/              # Bootstrap de backend remoto
│   ├── aws/               # Cria S3 bucket + DynamoDB table
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── gcp/               # Cria GCS bucket
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── README.md              # Este arquivo
```

## Workflows GitHub Actions

Existem dois workflows separados para deploy:

- **`.github/workflows/deploy-aws.yml`** - Deploy na AWS
- **`.github/workflows/deploy-gcp.yml`** - Deploy no GCP

Ambos os workflows seguem o mesmo padrão:
1. Autenticação no provedor (OIDC preferencial)
2. Execução do bootstrap para criar backend remoto (S3+DynamoDB ou GCS)
3. Geração dinâmica do arquivo `backend.hcl`
4. Execução de `terraform init/plan/apply`
5. Publicação dos outputs

## Como Usar Localmente

### AWS

1. **Bootstrap do backend (primeira vez apenas)**:
   ```bash
   cd infra/terraform/bootstrap/aws
   terraform init
   terraform apply \
     -var="region=us-east-1" \
     -var="state_bucket_name=my-terraform-state-bucket" \
     -var="dynamodb_table_name=my-terraform-locks" \
     -var="environment=prod"
   ```

2. **Configure o backend**:
   ```bash
   cd ../../aws
   cp backend.hcl.example backend.hcl
   # Edite backend.hcl com os valores retornados pelo bootstrap
   ```

3. **Deploy da infraestrutura**:
   ```bash
   terraform init -backend-config=backend.hcl
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

### GCP

1. **Bootstrap do backend (primeira vez apenas)**:
   ```bash
   cd infra/terraform/bootstrap/gcp
   terraform init
   terraform apply \
     -var="project=my-gcp-project" \
     -var="region=us-central1" \
     -var="state_bucket_name=my-terraform-state-bucket" \
     -var="environment=prod"
   ```

2. **Configure o backend**:
   ```bash
   cd ../../gcp
   cp backend.hcl.example backend.hcl
   # Edite backend.hcl com os valores retornados pelo bootstrap
   ```

3. **Deploy da infraestrutura**:
   ```bash
   terraform init -backend-config=backend.hcl
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

## Autenticação

### AWS

**Opção 1: OIDC (Recomendado para GitHub Actions)**
- Configure `AWS_ROLE_TO_ASSUME` no secrets do repositório
- O workflow assume a role automaticamente usando Workload Identity

**Opção 2: Credenciais estáticas**
- Configure `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` nos secrets
- Não recomendado para produção

**Localmente**:
- Configure AWS CLI: `aws configure`
- Ou use variáveis de ambiente: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### GCP

**Opção 1: Workload Identity Federation (Recomendado para GitHub Actions)**
- Configure `GCP_WIF_PROVIDER` e `GCP_SA_EMAIL` nos secrets
- O workflow autentica automaticamente

**Opção 2: Service Account Key**
- Configure `GCP_SA_KEY` nos secrets (JSON da chave)
- Não recomendado para produção

**Localmente**:
- Autentique com: `gcloud auth application-default login`
- Ou use service account: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

## Migração de Estado Existente

Se você já tem estado remoto configurado e está migrando para esta nova estrutura:

### Para AWS:

1. **Backup do estado atual**:
   ```bash
   cd infra/terraform  # diretório antigo
   terraform state pull > /tmp/terraform.tfstate.backup
   ```

2. **Inicialize o novo diretório com migração**:
   ```bash
   cd aws  # novo diretório
   cp /tmp/terraform.tfstate.backup .
   terraform init -backend-config=backend.hcl -migrate-state
   ```

3. **Verifique os recursos**:
   ```bash
   terraform state list
   terraform plan  # deve mostrar "No changes"
   ```

### Para GCP:

Processo similar ao AWS, mas trabalhando com o diretório `gcp/`.

## Variáveis e Secrets Necessários

### AWS Workflow
**Secrets**:
- `AWS_ROLE_TO_ASSUME` (OIDC) OU `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (opcional, padrão: us-east-1)

### GCP Workflow
**Secrets**:
- `GCP_PROJECT` (obrigatório)
- `GCP_WIF_PROVIDER` + `GCP_SA_EMAIL` (OIDC) OU `GCP_SA_KEY`
- `GCP_REGION` (opcional, padrão: us-central1)
- `GCP_ZONE` (opcional, padrão: us-central1-a)

## Segurança e Boas Práticas

1. **Backend remoto sempre**:
   - Use S3+DynamoDB (AWS) ou GCS (GCP) para estado
   - Habilite versionamento e criptografia
   - Nunca comite `backend.hcl` com valores reais

2. **Autenticação**:
   - Prefira OIDC/Workload Identity sobre credenciais estáticas
   - Use roles/service accounts com permissões mínimas necessárias
   - Rotate credentials regularmente

3. **Controle de acesso**:
   - Use branch protection para workflows de produção
   - Configure GitHub Environments com approvals
   - Restrinja quem pode executar workflows manualmente

4. **Logs e auditoria**:
   - Revise logs dos workflows regularmente
   - Use CloudTrail (AWS) ou Cloud Audit Logs (GCP)
   - Monitore alterações no estado do Terraform

5. **Secrets**:
   - Nunca comite secrets no código
   - Use SSM Parameter Store (AWS) ou Secret Manager (GCP)
   - Prefira variáveis `sensitive = true` no Terraform

## Troubleshooting

### "Bucket already exists" no bootstrap
- O bucket já foi criado anteriormente
- Use o bucket existente ou escolha um nome diferente
- Para GCS, lembre-se que nomes de buckets são globalmente únicos

### "Backend initialization required" após migração
```bash
terraform init -backend-config=backend.hcl -reconfigure
```

### "State lock" não liberado
```bash
# AWS
aws dynamodb delete-item \
  --table-name <table-name> \
  --key '{"LockID":{"S":"<workspace>/<path>/terraform.tfstate-md5"}}'

# GCP: locks são gerenciados automaticamente, expire após timeout
```

### Importar recursos existentes
```bash
# AWS EC2 instance
terraform import aws_instance.provision i-0123456789abcdef0

# GCP Compute instance
terraform import google_compute_instance.provision projects/<project>/zones/<zone>/instances/<name>
```

## Checklist Pós-Deploy

### AWS
- [ ] Backend S3 + DynamoDB criados e acessíveis
- [ ] `terraform output` mostra valores corretos
- [ ] EC2 visível no Systems Manager (se criado)
- [ ] Instance profile tem permissões SSM e S3
- [ ] Security groups configurados corretamente

### GCP
- [ ] Backend GCS criado e acessível
- [ ] `terraform output` mostra valores corretos
- [ ] Compute instance visível no console (se criado)
- [ ] Service account configurado corretamente
- [ ] Regras de firewall adequadas

## Manutenção

### Limpeza de recursos
```bash
# Destroy recursos primeiro
cd infra/terraform/aws  # ou gcp
terraform destroy

# Depois, limpe o bootstrap se necessário
cd ../bootstrap/aws  # ou gcp
terraform destroy
```

### Atualização de providers
Edite `version.tf` (AWS) ou `gcp-provider.tf` (GCP) e execute:
```bash
terraform init -upgrade
terraform plan
```

## Referências

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GitHub Actions OIDC AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [GitHub Actions Workload Identity GCP](https://github.com/google-github-actions/auth)