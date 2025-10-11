# Provisionamento de Dispositivos

Este projeto é uma API Django que integra provisionamento de dispositivos, utilizando MySQL para os dados principais e MongoDB como base de templates de configuração (XML/CFG) para cada modelo de device.

## Configuração de Ambiente

1. **Clone o repositório:**
   ```sh
   git clone https://github.com/snebur84/projeto_integracao_provisionamento.git
   cd projeto_integracao_provisionamento
   ```

2. **Crie o arquivo `.env` na raiz com as variáveis:**
   ```dotenv
   # MySQL
   MYSQL_DATABASE=seu_banco_mysql
   MYSQL_USER=seu_usuario_mysql
   MYSQL_PASSWORD=sua_senha_mysql
   MYSQL_HOST=db
   MYSQL_PORT=3306

   # MongoDB
   MONGODB_HOST=mongo
   MONGODB_PORT=27017
   MONGODB_DB_NAME=seu_banco_mongo
   MONGODB_USER=usuario_mongo
   MONGODB_PASSWORD=senha_mongo
   ```

3. **Instale as dependências:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Migre o banco MySQL:**
   ```sh
   python manage.py migrate
   ```

5. **(Opcional) Suba o ambiente com Docker Compose:**
   ```sh
   docker-compose up --build
   ```
   O `docker-compose.yml` já inclui serviços para MySQL, MongoDB e a aplicação Django.

## Uso da API

- O endpoint de download usa GET e espera User-Agent no formato: `vendor model version identifier`.
- O arquivo baixado é gerado dinamicamente com base nas configurações do device (MySQL) e no template correspondente (MongoDB).
- O nome do arquivo pode ser passado na URL, inclusive `.xml` ou `.cfg`.

## Variáveis de Ambiente Importantes

Certifique-se de preencher todas variáveis de ambiente no `.env` para conectar aos bancos MySQL e MongoDB.

## CI/CD na AWS

O workflow de CI/CD (`.github/workflows/ci-cd-aws.yml`) usa secrets para AWS e depende dos serviços MySQL e MongoDB. Veja instruções nos comentários do arquivo para configuração dos secrets.

---
