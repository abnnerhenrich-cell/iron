# IRON V49 — Correção definitiva do envio Web Push

## Causa encontrada
A inscrição do celular podia ser criada corretamente, mas o servidor entregava ao
`pywebpush` o conteúdo PEM da chave privada como uma string. A biblioteca espera
um caminho para arquivo PEM ou uma chave DER/RAW codificada em Base64URL.
Com isso, o envio real falhava mesmo com o aparelho aparentemente ativado.

## Correções
- Chave privada VAPID enviada ao pywebpush como scalar P-256 RAW de 32 bytes em Base64URL.
- Chave pública continua derivada exatamente do mesmo par.
- Timeout de 8 segundos no serviço push para não travar requisições.
- Logs do status/resposta do serviço Push para diagnóstico.
- Novo endpoint `/push/test`.
- Ao tocar em Ativar, o IRON agora exige um teste de entrega real antes de considerar o aparelho ativado.
- O usuário deve receber: “IRON — notificações ativadas”.
- Se o teste não chegar, a ativação é considerada incompleta e o app informa.
- Mantidas as notificações internas e todas as funções anteriores.
- Nenhum histórico ou dado existente é apagado.
