# ChatMemoryAPI
Este repositório contém o código da API que gerencia o histórico de conversas para aplicações de chatbot. Desenvolvida com FastAPI e implantada na AWS, a API envia dados para um banco de dados PostgreSQL no RDS (também hospedado na AWS).

## Autenticação
A API suporta dois métodos de autenticação:

1. **Autenticação Simples**: Login simples por nome de usuário (sem senha)
2. **Autenticação Auth0**: Login seguro via Auth0

### Configurando o Auth0

1. Crie uma conta no [Auth0](https://auth0.com/)
2. Configure uma aplicação (Regular Web Application)
3. Configure as URLs de callback permitidas
4. Configure as seguintes variáveis de ambiente no arquivo `.env`:
   - `AUTH0_DOMAIN`
   - `AUTH0_CLIENT_ID`
   - `AUTH0_CLIENT_SECRET`
   - `AUTH0_CALLBACK_URL`
   - `AUTH0_AUDIENCE` (opcional)

## Instalação

1. Clone o repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Crie um arquivo `.env` baseado no `.env.example`
4. Execute a aplicação:
   ```
   uvicorn api.api:app --reload
   ```

## Endpoints de Autenticação

- `/auth/login-simple`: Login simplificado por nome de usuário
- `/auth/login`: Redirecionamento para o login do Auth0
- `/auth/callback`: Callback para processar o login do Auth0
- `/auth/token`: Endpoint alternativo para SPAs trocarem o código de autorização por tokens
