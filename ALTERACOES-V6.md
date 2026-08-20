# IRON V6 — correção de recusas e progresso

- Corrigido o cálculo de **Em análise** para considerar exclusivamente entregas com status `pending`.
- Entregas `rejected` permanecem no histórico, mas não contam na porcentagem, nem no saldo reservado da meta.
- Revisão administrativa agora usa bloqueio transacional (`FOR UPDATE`) e impede dupla decisão concorrente.
- Ao recusar, o sistema confirma explicitamente que o valor saiu de **Em análise**.
- Páginas dinâmicas recebem cabeçalhos `no-store/no-cache` para não exibir percentuais antigos.
- Ao retornar para uma página pelo cache de navegação (BFCache), o IRON recarrega os dados do servidor.
- Arquivos estáticos continuam cacheáveis pelo PWA, mantendo o site otimizado.
