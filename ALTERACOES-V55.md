# IRON V55 — Hardening, performance e segurança

## Segurança
- Corrigida recuperação de senha insegura: o site não exibe mais link de redefinição publicamente para quem apenas conhece o e-mail.
- Hierarquia ganhou tela própria para gerar link temporário de 30 minutos para membro/gerente.
- Troca de senha continua revogando todos os dispositivos persistentes antigos.
- Cabeçalhos HTTP defensivos: nosniff, anti-frame, referrer policy, permissions policy e HSTS em produção.
- Mantidas CSRF, cookies HttpOnly/SameSite/Secure e autorização por função/estado da conta.

## Banco e performance
- Conexões PostgreSQL com connect timeout.
- statement_timeout, lock_timeout e idle transaction timeout evitam requests presos indefinidamente.
- Índices novos para usuários, metas, submissões, lotes, fechamentos e créditos.
- Índice parcial garante apenas um ciclo/meta ativo por vez, inclusive sob concorrência.
- Índice case-insensitive protege unicidade de e-mail.

## Estabilidade
- Removido handler 413 duplicado/inconsistente.
- Mantido cache dinâmico desativado e PWA atualizado para V55.
- Nenhuma alteração destrutiva de dados.
- Estrutura continua compatível com Neon/Vercel e deploy via GitHub.

## Validação
- Python compilado com sucesso.
- Todos os templates Jinja compilados.
- Formulários POST verificados para CSRF.
