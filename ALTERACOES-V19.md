# IRON V19 — Correção do fechamento de metas
- Removida agregação da mesma consulta que usa FOR UPDATE.
- As metas são bloqueadas primeiro e os totais aprovados são somados separadamente.
- Migrações de fechamento/crédito ficaram idempotentes para bancos vindos de versões anteriores.
- Corrigido o cálculo de saldo negativo aplicado no fechamento.
- Mantidas as opções de transportar saldo positivo, negativo, ambos ou nenhum.
