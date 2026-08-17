# IRON Metas — Vercel + Neon

Versão preparada para publicação na Vercel com PostgreSQL Neon.

## O que esta versão faz

- Login e cadastro de usuários.
- Painel de usuário.
- Painel administrativo.
- Criação de ciclos e metas.
- Entrega de quantidade/valor.
- Aprovação e reprovação pelo administrador.
- Histórico.
- Usuários, metas e entregas persistidos no Neon.
- Comprovantes em imagem persistidos no próprio PostgreSQL nesta primeira versão.

## Variáveis na Vercel

A integração Neon deve criar automaticamente:

`DATABASE_URL`

No projeto da Vercel, configure também:

`SECRET_KEY` = uma chave longa e aleatória  
`ADMIN_EMAIL` = o e-mail do administrador  
`ADMIN_PASSWORD` = a senha inicial do administrador

Caso não configure os dados de administrador, o primeiro admin será:

E-mail: `admin@iron.local`  
Senha: `admin123`

Troque isso antes do uso real.

## Uploads

PNG, JPG, WEBP ou GIF, até 3,5 MB por imagem.

## Deploy

Substitua os arquivos do repositório GitHub pelos arquivos desta versão.
A Vercel fará um novo deploy automaticamente.


## Correção de login do administrador

Nesta versão, quando `ADMIN_EMAIL` e `ADMIN_PASSWORD` estão configurados na Vercel,
o sistema cria ou atualiza automaticamente esse usuário como administrador ativo.
Isso resolve bancos que já tinham sido inicializados com credenciais antigas.


## Painéis separados e permissões

- Membros entram em `/login`.
- Administradores entram em `/admin/login`.
- Novos cadastros ficam aguardando aprovação.
- No Painel Admin > Usuários, um admin pode:
  - aprovar ou recusar novos membros;
  - bloquear/desbloquear contas;
  - conceder permissão de administrador;
  - remover permissão de administrador.


## Correção de entregas e fotos

- Corrigida a rota das imagens no painel Admin.
- Entregas pendentes aparecem em `Admin > Entregas`.
- O administrador consegue abrir a foto/comprovante e aprovar ou reprovar.
- O envio de imagem agora é obrigatório para novas entregas.
- O painel inicial do Admin destaca quantas entregas estão aguardando análise.


## Solicitações de cadastro — correção

- Novo menu Admin > Cadastros.
- Todo novo membro entra com `approved = false`.
- O painel Admin mostra a quantidade de cadastros aguardando aprovação.
- A tela `/admin/registrations` lista nome, e-mail e data do pedido.
- O administrador pode Aprovar ou Recusar diretamente nessa tela.


## Correção da validação do cadastro

A validação do cadastro agora informa separadamente:
- nome inválido;
- e-mail inválido;
- senha menor que 6 caracteres;
- e-mail já cadastrado.

Nome e e-mail permanecem preenchidos caso ocorra algum erro.


## Entrega múltipla

A tela de atualização agora permite:
- pesquisar materiais;
- informar vários itens no mesmo envio;
- usar botões + e -;
- adicionar observação única para o envio;
- anexar até 3 fotos;
- enviar todos os itens de uma vez;
- o Admin continua recebendo cada item para aprovação, com acesso às fotos.


## Correção Vercel 413 / imagens

A Vercel limita o corpo total da requisição da Function.
Nesta versão:
- as fotos são redimensionadas no navegador antes do envio;
- são convertidas para JPEG;
- cada arquivo otimizado fica limitado a aproximadamente 1,2 MB;
- até 3 fotos cabem com margem dentro do limite total da requisição.
