# IRON V14 — Aprovação por atualização

- Corrigida a análise de entregas com vários produtos.
- Aprovar um produto de uma atualização agora aprova todos os produtos pendentes do mesmo `batch_id`.
- Recusar uma atualização também recusa todos os produtos pendentes do mesmo lote.
- Entregas antigas sem `batch_id` continuam funcionando individualmente.
- A mensagem de confirmação informa quantos produtos foram analisados.
