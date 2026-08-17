# RPT Metas — sistema de metas e entregas

Aplicação web completa em Flask + SQLite, com visual responsivo escuro/laranja inspirado nas referências enviadas.

## Recursos

- Cadastro e login de usuários
- Perfis `user` e `admin`
- Painel de metas da semana/ciclo
- Criação de ciclos e metas pelo administrador
- Entrega de quantidade ou valor por meta
- Upload de imagem como comprovante
- Histórico de entregas
- Fluxo de aprovação/reprovação pelo admin
- Progresso calculado apenas com entregas aprovadas
- Banco SQLite persistente
- Uploads salvos em `instance/uploads`
- Proteção simples contra CSRF
- Senhas com hash do Werkzeug
- Limite de upload de 8 MB e validação de extensão

## Como rodar

1. Instale Python 3.11+.
2. Na pasta do projeto:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

3. Instale:

```bash
pip install -r requirements.txt
```

4. Opcionalmente configure o primeiro administrador:

Windows PowerShell:

```powershell
$env:ADMIN_EMAIL="admin@empresa.com"
$env:ADMIN_PASSWORD="troque-esta-senha"
```

Linux/macOS:

```bash
export ADMIN_EMAIL="admin@empresa.com"
export ADMIN_PASSWORD="troque-esta-senha"
```

5. Rode:

```bash
python app.py
```

Acesse `http://127.0.0.1:5000`.

## Primeiro acesso

Se não houver nenhum admin, a aplicação cria automaticamente:

- E-mail: `admin@rpt.local`
- Senha: `admin123`

Troque isso antes de colocar em produção.

## Estrutura de dados

- `users`: usuários e administradores
- `cycles`: ciclos semanais
- `goals`: metas por ciclo
- `submissions`: entregas dos usuários com imagem e status

## Produção

Para produção, use um servidor WSGI (Gunicorn/Waitress), HTTPS e armazenamento externo de arquivos (S3/R2/Cloudinary). O SQLite funciona muito bem para ambiente pequeno/interno; para maior volume, migre para PostgreSQL.

