# IRON V57 — compatibilidade Neon Pooler

- Remove `statement_timeout`, `lock_timeout` e `idle_in_transaction_session_timeout` do startup packet do PostgreSQL.
- Mantém `connect_timeout=10`.
- Configura os timeouts por `SET` somente depois da conexão ser aceita pelo Neon.
- Corrige `FUNCTION_INVOCATION_FAILED` causado pelo endpoint `-pooler` rejeitar `options` no startup.
- Nenhuma limpeza ou alteração destrutiva no banco.
