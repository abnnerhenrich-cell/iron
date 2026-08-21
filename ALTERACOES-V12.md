# IRON V12 — Exclusão de meta personalizada

- Corrigido o botão de excluir meta personalizada quando a meta já possui entregas.
- Ao excluir a meta, suas submissions/histórico são removidos.
- Fotos antigas gravadas diretamente na submission são removidas junto com ela.
- Lotes de fotos (delivery_batches) que ficam sem nenhuma submission vinculada são removidos automaticamente.
- Se uma foto pertence a um envio compartilhado com outra meta, ela é preservada para não quebrar o histórico da outra meta.
- Exclusão feita em transação, com rollback em caso de erro.
