# Veterani — Integração Discord REST + OAuth2

## Configurar na Vercel (Environment Variables)

- `DISCORD_CLIENT_ID=1564340327249223720`
- `DISCORD_CLIENT_SECRET`: Client Secret do Developer Portal (não colocar no código)
- `DISCORD_BOT_TOKEN`: token do bot (não colocar no código)
- `DISCORD_REDIRECT_URI=https://veterani.vercel.app/discord/callback`
- `DISCORD_GUILD_ID=1319723201743552677`
- `DISCORD_MANAGEMENT_ROLE_ID=1564336547950493746`
- `DISCORD_META_CATEGORY_ID=1486815221619232839`
- `DISCORD_SALES_CHANNEL_ID=1556355351102628032`

Configure exatamente a mesma Redirect URI no Discord Developer Portal. Faça novo deploy após salvar as variáveis.

## Permissões

O bot precisa de Manage Channels, View Channels, Send Messages e Read Message History; seu cargo deve conseguir criar canais na categoria. O usuário deve ser membro do servidor antes de vincular.

## Eventos implementados

- Vinculação OAuth2 com `identify`, checagem de servidor e exclusividade da conta Discord.
- Canal privado após aprovação e vinculação; visível ao membro, cargo GERENCIA e bot (que deve ter as permissões efetivas).
- Meta personalizada: mensagem exclusiva no canal do membro com quantidade e prazo.
- Entrega criada: notificação no canal do membro.
- Nova venda: publicação no canal de vendas. Edição de venda não gera notificação duplicada.

## Limitações e cuidados

- As chamadas à API Discord são realizadas após a gravação no banco. Uma falha de API é registrada no log, mas não impede a operação do site; não há fila de reenvio automático nesta versão.
- Não altera nem apaga dados antigos. Colunas de Discord são adicionadas pelo `init_db()`.
- Um usuário que já vinculou e possui canal precisa de intervenção administrativa para trocar a conta Discord.
- O acesso do membro é verificado na vinculação. Se ele sair do servidor, o canal permanece, mas ele perde acesso pelo Discord.
- Teste primeiro em ambiente de homologação, especialmente a configuração de permissões do canal e as rotas OAuth2.
