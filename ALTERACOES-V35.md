# IRON V35 — Progresso final, logs de aprovação e contagem ao vivo

## Barra geral
- Painel do membro: progresso geral agora é segmentado.
- Painel Admin > pasta do membro: progresso geral segmentado.
- Lista de membros: cada pasta também mostra a barra segmentada.
- Verde = aprovado.
- Amarelo = em análise.
- Percentual final = aprovado + em análise.

## Auditoria
- Cadastro de membro agora registra:
  - quem aprovou;
  - data/hora da aprovação.
- Entregas/metas já utilizavam `reviewed_by`; agora o nome de quem aprovou/recusou é exibido no histórico.
- Membros antigos, aprovados antes desta versão, aparecem como “aprovado antes do log” quando não houver responsável registrado.

## Contagem de membros
- Dashboard da Hierarquia conta membros aprovados direto do banco.
- Gerentes também entram na contagem de membros cadastrados, pois continuam com Painel de Membro.
- Dashboard consulta os números novamente a cada 30 segundos e quando a janela recebe foco.
- Páginas HTML autenticadas recebem `no-store/no-cache`, evitando contagens antigas por cache do navegador/PWA.
