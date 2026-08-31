# IRON V42 — Correção do 403 na tela de login

## Causa encontrada
O bloqueio global do cargo Gerente analisava a sessão antes de abrir `/login`.
Se o navegador ainda tivesse uma sessão válida de Gerente, `/login` não estava
na lista de rotas permitidas e o Flask respondia 403 Forbidden.

Isso explica por que a guia anônima funcionava: nela não existia o cookie/sessão.

## Correção
- `/login` nunca mais é bloqueado pela restrição do Gerente.
- `/admin/login`, `/register`, `/logout`, manifest e service worker também foram
  explicitamente marcados como rotas públicas.
- Cookies que apontem para usuário inexistente são limpos ao abrir a tela de login.
- Mantida a limpeza de cache/sessão da V41.
- Service Worker atualizado para V42.
