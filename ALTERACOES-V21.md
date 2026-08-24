# IRON V21 — Excluir Fechamentos e Créditos

- Adicionado botão “Excluir fechamento” no Extrato de Metas.
- Ao excluir um fechamento, o IRON desfaz automaticamente o saldo positivo/negativo gerado.
- Se o saldo ainda estiver disponível, ele é removido do saldo.
- Se o saldo já tiver sido aplicado em uma meta posterior, a aplicação é revertida nessa meta.
- A meta original é reaberta para permitir correção e novo fechamento.
- Se o sistema não conseguir reverter todo o saldo com segurança, a exclusão é bloqueada para evitar inconsistência.
- Novos fechamentos passam a registrar exatamente o saldo transportado.
