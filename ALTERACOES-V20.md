# IRON V20 — Correção NotFound no Fechar Meta

- Corrigido o `NotFound` capturado durante o fechamento de metas.
- O fechamento agora localiza o membro somente pelo ID, sem exigir `role='user'`.
- Isso permite fechar corretamente metas de contas que tiveram permissão/role alterada.
- Usuário inexistente agora gera mensagem controlada e volta para a lista de membros.
- Erros HTTP reais (404/403) não são mais mascarados como erro de fechamento.
