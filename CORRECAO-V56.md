# IRON V56 — correção de inicialização na Vercel

- Remove falha fatal quando SECRET_KEY não está configurada.
- Prioriza SECRET_KEY da Vercel quando existente.
- Se ausente, deriva chave estável de sessão a partir da DATABASE_URL privada.
- Mantém todas as melhorias da V55.
- Nenhum dado do Neon é apagado ou alterado por esta correção.
