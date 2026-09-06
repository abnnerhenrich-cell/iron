# IRON V48 — Web Push Android/PWA reforçado

- Validação real da chave pública VAPID no servidor (87 caracteres / P-256).
- O celular compara a chave da inscrição existente com a chave atual do IRON.
- Inscrições antigas/incompatíveis são removidas e recriadas automaticamente.
- Aguarda o Service Worker atualizado antes da inscrição.
- Diagnóstico separado para: permissão bloqueada, configuração do servidor,
  falha ao salvar aparelho e inscrição antiga corrompida.
- Falha de push continua sem interferir no login/painel.
- Cache/Service Worker atualizado para V48.
- Nenhum dado de metas, membros, entregas, imagens, saldos ou histórico é apagado.
