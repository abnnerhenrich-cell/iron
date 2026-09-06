# IRON V50 — Aviso de notificações volta a aparecer

- Corrigido o comportamento do botão X no aviso de notificações.
- Antes, ao dispensar uma vez, o aviso podia ficar oculto permanentemente via localStorage.
- Agora o aviso fica oculto apenas por 24 horas e depois reaparece.
- Estados antigos de `iron_push_dismissed=1` são limpos automaticamente.
- Se as notificações estiverem BLOQUEADAS no navegador, o aviso continua voltando e mostra orientação para liberar manualmente.
- Se a permissão estiver concedida, mas a inscrição push não existir, o aviso reaparece automaticamente.
- Ao ativar com sucesso, o estado de dispensa temporária é limpo.
- Nenhum dado de metas, membros, entregas, histórico, imagens ou saldos é alterado.
