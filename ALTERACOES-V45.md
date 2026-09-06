# IRON V45 — Notificações de novas metas

- Criada Central de Notificações para membros.
- Ao criar uma nova meta/ciclo, todos os membros e gerentes ativos/aprovados recebem aviso.
- Ao adicionar metas de materiais a um membro, ele recebe uma notificação específica.
- Badge com quantidade de notificações não lidas.
- Aviso destacado no painel do membro.
- Tela de notificações com opção de abrir/marcar como lida e marcar todas como lidas.
- Histórico de notificações salvo no PostgreSQL/Neon.
- Sem alteração/destruição dos históricos de metas, entregas, saldos, imagens ou membros existentes.
- Mantidas todas as funções da V44.

Observação: esta versão cria notificações INTERNAS no IRON. Elas aparecem no app/site assim que o membro entra.
Push notification com o app totalmente fechado exigiria uma etapa adicional de Web Push (VAPID + subscriptions).
