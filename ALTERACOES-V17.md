# IRON V17 — Correção do erro 500 no painel do membro

- Corrigido erro após login de membros na V16.
- Campos NUMERIC do PostgreSQL (`target`, `approved`, `pending`, `credit_applied`) agora são normalizados para `float` antes dos cálculos.
- Evita erro de tipo `Decimal` x `float` nas porcentagens e na tela de Nova Entrega.
- Mantido integralmente o sistema de fechamento de metas e créditos da V16.
