# IRON V22 — Fechamento sai após entrar na nova meta

- Quando um saldo positivo ou negativo é aplicado na criação da próxima meta do mesmo produto, o fechamento anterior deixa automaticamente a área “Fechamentos e créditos”.
- O saldo também deixa de aparecer como disponível, pois já entrou na nova meta.
- O registro não é apagado fisicamente do banco; ele é marcado como consumido e vinculado à nova meta, preservando segurança e rastreabilidade.
- O botão “Excluir fechamento” continua disponível enquanto o fechamento ainda não tiver sido consumido.
- A nova meta mantém em `credit_applied` o saldo que recebeu, positivo ou negativo.
