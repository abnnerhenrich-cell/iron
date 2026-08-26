# IRON V34 — Reformulação geral

Esta versão mantém as regras e funções da V33 e adiciona uma camada ampla de melhoria de experiência, estabilidade e segurança.

## Interface
- Novo acabamento visual do painel em preto/prata, mais limpo e consistente.
- Melhor contraste, espaçamento, tipografia, cartões, botões e campos.
- Sidebar refinada e estados ativos mais evidentes.
- Dashboard e cards com hierarquia visual mais clara.
- Login e cadastro redesenhados para aparência mais profissional.
- Tabelas com contêiner próprio, cabeçalho estável e melhor leitura.
- Melhor feedback de hover/foco e suporte a `prefers-reduced-motion`.

## Celular
- Navegação inferior em formato flutuante com safe-area para iPhone.
- Topbar fixa com blur e botões maiores para toque.
- Cards, formulários, metas, perfil e tabelas ajustados para telas pequenas.
- Melhor aproveitamento de largura em 430px ou menos.

## UX e confiabilidade
- Bloqueio de envio duplicado em formulários POST para evitar registros repetidos.
- Feedback visual no botão durante gravações.
- Confirmação padronizada para ações destrutivas que não possuíam confirmação própria.
- Link de acessibilidade “Pular para o conteúdo”.

## Segurança
- Sessões de usuários bloqueados ou não aprovados deixam de continuar válidas ao navegar.
- A mesma validação passa a valer para Admin e Gerente.
- Cabeçalhos `nosniff`, `SAMEORIGIN`, `Referrer-Policy`, `Permissions-Policy` e HSTS em HTTPS.
- Acesso negado agora retorna o usuário para um painel válido com mensagem amigável, em vez de uma tela 403 seca.

## Compatibilidade
- Mantido o acesso duplo de Admin/Gerente ao painel de membro.
- Mantidas as restrições do cargo Gerente: Cadastros, Calculadora e Compras & Vendas no ambiente administrativo.
- Nenhuma tabela ou regra de negócio existente foi removida.
