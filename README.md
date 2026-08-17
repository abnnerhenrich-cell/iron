# RPT Metas — Vercel + Neon

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

E-mail: `admin@rpt.local`  
Senha: `admin123`

Troque isso antes do uso real.

## Uploads

PNG, JPG, WEBP ou GIF, até 3,5 MB por imagem.

## Deploy

Substitua os arquivos do repositório GitHub pelos arquivos desta versão.
A Vercel fará um novo deploy automaticamente.
