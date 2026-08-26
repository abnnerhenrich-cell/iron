# IRON V35 — Command Center

Esta versão mantém as funcionalidades e regras de negócio da V34, mas reconstrói a camada visual para criar uma experiência realmente diferente.

## Interface
- Nova identidade “IRON Command Center” em grafite + azul elétrico.
- Sidebar desktop flutuante e compacta, com estado ativo muito mais evidente.
- Nova navegação mobile em dock flutuante e topbar translúcida.
- Login reconstruído em layout de duas áreas no desktop e versão compacta no celular.
- Heroes, painéis, cards, indicadores, botões, tabelas e formulários redesenhados.
- Dashboard de membro com progresso circular mais destacado e metas em cards mais claros.
- Dashboard administrativo transformado em central de operação com atalhos e KPIs mais fortes.
- Compras & Vendas, filtros e histórico recebem a mesma linguagem visual.
- Melhor contraste, hierarquia tipográfica e espaçamento.

## Responsividade
- Breakpoints novos para tablet e celular.
- Bottom navigation redesenhada.
- Formulários passam de duas colunas para uma coluna em telas pequenas.
- Cards e tabelas adaptados para leitura mais confortável.

## Compatibilidade
- Nenhuma rota ou regra de negócio foi removida.
- Permissões de Admin/Gerente/Membro permanecem intactas.
- A nova camada visual fica isolada em `static/v35.css`, facilitando manutenção ou rollback.
