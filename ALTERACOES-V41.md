# IRON V41 — Correção de acesso somente em guia anônima

Sintoma:
- alguns usuários só conseguiam entrar corretamente usando aba/guia anônima.

Correções:
- novo nome de cookie de sessão (`iron_session_v41`) para não reutilizar cookies antigos ou corrompidos;
- cookie explicitamente válido para todo o site (`/`);
- páginas dinâmicas continuam com `no-store/no-cache`;
- Service Worker atualizado para V41;
- Service Worker passa a ser registrado com `updateViaCache: none`;
- navegador solicita atualização do Service Worker em cada carregamento;
- caches antigos do PWA são removidos na ativação da nova versão;
- arquivos estáticos recebem nova versão de cache.

Observação:
- ao publicar esta versão, sessões antigas serão descartadas por causa do novo nome do cookie.
- os usuários precisarão fazer login novamente uma vez. Depois disso o acesso normal deve funcionar sem guia anônima.
