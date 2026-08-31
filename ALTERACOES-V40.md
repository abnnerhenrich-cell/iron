# IRON V40 — Percentual do membro sincronizado com o Admin

Correção principal:
- O Painel do Membro agora calcula o percentual geral exatamente com a mesma regra do Admin.
- Cada material/meta tem o mesmo peso na porcentagem final.
- Antes o painel do membro somava quantidades brutas; isso fazia metas maiores pesarem mais e gerava um número diferente do Admin.
- Agora cada material é calculado individualmente e depois é feita a média.
- A parte Em análise também segue a mesma regra e é limitada ao espaço restante de cada meta.
- O gráfico circular continua mostrando Aprovado + Em análise.
