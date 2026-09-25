# IRON V54 — Auditoria geral e correções
- Sessões antigas de contas bloqueadas/inativas/não aprovadas não mantêm acesso.
- Redefinir senha revoga tokens de “Manter conectado”.
- Metas personalizadas são salvas antes das notificações; falha de push não desfaz a meta.
- Notificação individual ganhou migração defensiva.
- SECRET_KEY padrão insegura foi removida em produção.
- Cache/PWA atualizado.
- Python e templates Jinja validados.
- Nenhum histórico ou dado de membro é apagado.

IMPORTANTE: confirme `DATABASE_URL` e `SECRET_KEY` nas Environment Variables da Vercel.
Não altere a SECRET_KEY depois do deploy.
