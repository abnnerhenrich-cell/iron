# IRON V47 — Correção do Push e proteção do login

## Correção principal
Na V46 a chave pública VAPID começava com os bytes do texto `\\x04`, em vez do
byte P-256 real `0x04`. Isso fazia `pushManager.subscribe()` falhar em aparelhos
compatíveis e gerava o aviso “Não foi possível ativar as notificações”.

## O que mudou
- Chave pública VAPID corrigida para o formato P-256 uncompressed correto (65 bytes).
- A chave pública é sempre derivada da chave privada persistida no Neon.
- Instalações V46 com chave pública inválida são corrigidas automaticamente no primeiro uso.
- O contador de notificações virou recurso não crítico: se ele falhar, login e painel continuam funcionando.
- Fluxo de inscrição push ficou mais defensivo e recria inscrições incompatíveis quando necessário.
- Service Worker/cache atualizado para V47.
- Nenhum histórico de metas, membros, entregas, imagens, compras/vendas ou saldos é removido.

## Depois do deploy
O membro deve abrir o IRON e tocar novamente em “Ativar”.
Se o navegador tiver sido configurado anteriormente para bloquear notificações,
é necessário liberar a permissão nas configurações do site/app antes de tentar.
