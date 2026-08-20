# IRON V7 — Login persistente

- Adicionada opção **Manter conectado neste dispositivo** no login de membros.
- A mesma opção também foi adicionada ao login administrativo.
- Quando marcada, a sessão permanece válida por até 30 dias.
- Quando desmarcada, o comportamento continua sendo o de sessão normal do navegador.
- O IRON não armazena a senha em cookie; apenas a sessão autenticada.
- Cookies continuam com HttpOnly, SameSite=Lax e Secure em produção na Vercel.
- A sessão persistente é renovada enquanto o usuário continua utilizando o sistema.
