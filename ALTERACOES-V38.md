# IRON V38 — Correção do erro 500 na pasta do membro

- Corrigida a rota Admin > Membros > Pasta do membro.
- A tela agora é compatível mesmo se as colunas de auditoria `approved_by` e
  `approved_at` ainda não tiverem sido criadas no banco.
- O recurso de log de quem aprovou continua funcionando quando as colunas estão disponíveis.
- A ação de aprovar cadastro também garante a criação das colunas antes de gravar o log.
- Mantidas as melhorias da V37: gráfico circular, contagem de membros ativos e alerta Em análise.
