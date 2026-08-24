# IRON V23 — Exclusão manual + automática de fechamentos

- Mantido o comportamento automático da V22:
  - ao criar a nova meta do mesmo produto e aplicar o saldo, o fechamento antigo sai automaticamente da área pendente.
- Mantida/adicionada a opção manual:
  - enquanto o fechamento ainda estiver pendente, o admin pode clicar em “Excluir fechamento”.
  - ao excluir manualmente, o saldo positivo/negativo gerado é desfeito.
  - a meta original é reaberta para correção e novo fechamento.
- Fechamentos já consumidos pela nova meta continuam arquivados internamente para segurança e rastreabilidade.
