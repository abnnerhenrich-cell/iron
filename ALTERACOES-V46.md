# IRON V46 — Push real no celular

- Web Push real implementado para membros e gerentes.
- O membro toca em “Ativar” e concede permissão de notificações no dispositivo.
- As inscrições push ficam salvas no Neon e vinculadas à conta/membro.
- Ao lançar uma nova meta, o servidor envia push aos dispositivos inscritos.
- Ao adicionar metas específicas a um membro, esse membro recebe push.
- O push abre o IRON ao ser tocado.
- Inscrições expiradas (404/410) são removidas automaticamente.
- Chaves VAPID são geradas uma única vez e armazenadas no Neon, sem expor a chave privada no GitHub.
- Mantida também a Central de Notificações interna da V45.
- Nenhum histórico de metas, membros, entregas, imagens ou saldos é apagado.

## iPhone/iPad
Para Web Push no iPhone/iPad, instale o IRON pela opção “Adicionar à Tela de Início” no Safari
e depois abra o app instalado para autorizar notificações.

## Android/Chrome e desktop
Basta entrar no IRON e tocar em “Ativar” quando o aviso aparecer.

Dependência adicionada:
- pywebpush==2.5.0
