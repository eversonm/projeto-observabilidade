# Instruções para agentes e desenvolvedores

## Estrutura e regras

- Este diretório é a raiz isolada do projeto; não altere a API de referência para implementar esta atividade.
- Mantenha a separação entre rotas, serviços, repositórios, modelos e schemas em `app/`.
- Valide entrada e saída com Pydantic; use SQLAlchemy assíncrono e consultas parametrizadas.
- Mudanças de produtos exigem role Keycloak `products-user` ou `products-admin`; `/init` exige `products-admin`.
- Preserve limites de tamanho dos campos, paginação, mensagens de erro sem detalhes internos e logs sem tokens, senhas ou corpos de requisição.
- Labels Prometheus devem ter cardinalidade limitada; use o template da rota, método e classe de status, nunca IDs de produto/usuário.
- Logs de containers vão para Loki via Alloy; traces OpenTelemetry vão para Tempo pelo Collector.
- O webhook do Alertmanager é somente interno à rede Docker. A API e as portas de métricas são vinculadas ao loopback local; não publique-as em uma rede externa.

## Ambiente de desenvolvimento

```sh
uv sync --group dev
uv run pytest
uv run ruff check app tests
uv run mypy app
uv run bandit -r app
uv run pip-audit
```

Quando houver acesso ao índice de pacotes, gere e mantenha `uv.lock` atualizado junto com `pyproject.toml`. O build local usa `uv sync` com as dependências do projeto; evite atualizar dependências sem revisar compatibilidade e resultado do scanner.

## Serviços e smoke test

```sh
cp .env.example .env
docker compose up --build -d
docker compose ps
curl -fsS http://localhost:8000/health/live
curl -fsS http://localhost:8000/health/ready
```

Crie usuário e role no realm Keycloak `observabilidade` para testar rotas protegidas. Confira Prometheus em `http://localhost:9090/targets`, Grafana em `http://localhost:3000`, os logs dos containers no Loki e spans da API no Tempo. Confira o webhook disparando e resolvendo alertas antes de aceitar alterações na regra de MTTR.

## Carga inicial

`sql/init_products.sql` é a fonte da verdade para a criação em massa. A carga alvo padrão é 2 milhões; o benchmark em savepoint é revertido e a estratégia efetiva é selecionada pelo tempo medido (<30 s: 100 inserções individuais e o restante bulk; caso contrário: bulk). Preserve advisory lock, idempotência e execução transacional ao alterar a implementação.

