# IRON V53 — Correção do erro ao criar meta

- A criação da meta agora é salva antes de qualquer notificação.
- Falha de notificação interna ou Web Push não cancela mais a meta.
- Migração defensiva da tabela e índice de notificações.
- Validação das datas antes de gravar no banco.
- Erros durante a criação são tratados sem página 500.
- Mantidas todas as funções da V52.
- Nenhum histórico, membro, entrega, imagem, saldo ou compra/venda é apagado.
