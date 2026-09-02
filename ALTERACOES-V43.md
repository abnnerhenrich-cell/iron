# IRON V43 — Redefinição de senha pelo membro

- Adicionado “Esqueci minha senha” no login.
- Membro informa o e-mail cadastrado.
- Sistema gera um link seguro assinado, válido por 30 minutos.
- Link permite criar e confirmar uma nova senha.
- Senha continua armazenada somente como hash.
- Admin não vê e não escolhe a senha do membro.
- Contas bloqueadas/não aprovadas não podem redefinir por esse fluxo.
- Mantidas todas as funções da V42.

IMPORTANTE:
Esta versão não envia e-mail automaticamente porque o projeto ainda não possui
um serviço de e-mail configurado. O link temporário é apresentado na própria
tela ao membro. Para enviar o link por e-mail automaticamente será necessário
configurar um provedor de e-mail transacional.
