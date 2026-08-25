# IRON V33 — Estabilidade no upload de comprovantes

- Compressão automática reforçada no navegador antes do envio.
- Fotos são redimensionadas para no máximo 1280 px no maior lado.
- Compressão adaptativa tenta manter cada comprovante abaixo de ~720 KB.
- Servidor rejeita imagens acima de 950 KB e conjunto acima de 2,8 MB.
- Limite HTTP ampliado para 8 MB para evitar erro antes da otimização/validação.
- Mensagem específica para erro 413 (arquivo grande), em vez de parecer site fora do ar.
- Estado visual: preparando fotos, prontas e enviando.
- Botão fica bloqueado durante otimização e envio para impedir duplicidade.
- Falhas no banco durante o upload são tratadas com rollback e mensagem clara.
- Nenhuma entrega parcial é salva se o banco/conexão falhar no meio.
- Mantidas até 3 imagens por atualização.
