# IRON — Refinamento visual e de usabilidade V3

## Visual e responsividade
- Mantida a identidade preto/prata.
- Tipografia refinada usando fontes nativas modernas, sem dependências externas.
- Tamanhos fluidos com `clamp()` para celular, tablet e desktop.
- Microanimações leves baseadas em opacity/transform.
- Suporte a `prefers-reduced-motion`.
- Cards, botões, navegação e barras de progresso com transições mais suaves.
- Ajustes específicos para telas grandes, notebooks, tablets, celulares e telas pequenas.
- Nenhuma biblioteca visual ou fonte externa adicionada, preservando desempenho.

## Painel administrativo
- Hero principal substituído por “Painel da Hierarquia”.
- Removido o texto explicativo antigo da central administrativa.
- Removida a frase sobre áreas separadas dos membros.
- Membros ordenados alfabeticamente por nome, ignorando maiúsculas/minúsculas.
- Campo “Categoria” removido do formulário de metas.
- “Quantidade / alvo” renomeado para “Quantidade”.
- Categoria removida da exibição visual das metas e do resumo do ciclo.

## Painel do membro
- Removido o texto explicativo abaixo da saudação.
- Progresso agora considera `aprovado + em análise` imediatamente após o envio.
- Barra das metas exibe aprovado e em análise como segmentos distintos.
- Área de perfil mostra somente o nome do membro junto da foto e ações de foto.
- Removidos os textos “Seu perfil” e a explicação de formatos/tamanho.
- Categoria removida dos cards de meta.

## Nova entrega
- Removidos “ATUALIZAÇÃO PARCIAL” e o parágrafo explicativo solicitado.
- Mantido o fluxo otimizado de seleção, compressão das imagens e envio para revisão.
