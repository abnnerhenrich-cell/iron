# IRON V16 — Fechamento de Metas e Crédito de Excedentes

## Novo fluxo
- A Hierarquia pode fechar as metas personalizadas de um membro ao fim do período.
- O fechamento só é permitido quando não existem entregas pendentes de análise.
- O sistema compara a quantidade necessária com o total aprovado.
- Excedente aprovado vira crédito para a próxima meta com o mesmo nome e unidade.
- Quantidade faltante fica registrada no histórico, mas não é carregada para a próxima meta.
- A próxima meta mantém a quantidade original e mostra separadamente o crédito aplicado e a quantidade realmente necessária.

## Conferência administrativa
- A aba Metas Personalizadas mostra:
  - Meta original
  - Crédito anterior
  - Necessário
  - Aprovado
  - Em análise
  - Excedente ou falta
- A aba Entregas e Aprovações ganhou um Extrato de Metas com todos os fechamentos.
- O saldo atual de créditos aparece para a Hierarquia.

## Entregas excedentes
- O membro pode enviar acima da quantidade necessária.
- A porcentagem visual continua limitada a 100%.
- O excedente só vira crédito depois do fechamento da Hierarquia.

## Segurança de dados
- Créditos são registrados por membro + nome da meta + unidade.
- Ao excluir uma meta ainda aberta que consumiu crédito anterior, o crédito é devolvido ao saldo.
- Páginas dinâmicas continuam fora do cache do PWA.
