# IRON V5 — correção definitiva

- Corrigido o HUD da Meta Ativa com layout próprio e sem sobreposição de textos.
- CSS recebeu versionamento `?v=5.0.0` para impedir que a Vercel/navegador continue exibindo a versão antiga.
- Service Worker trocado de cache-first para network-first nos arquivos estáticos.
- Cache antigo é removido na ativação do novo Service Worker.
- Botão Instalar IRON fica disponível mesmo quando o navegador não dispara `beforeinstallprompt`; nesse caso mostra instruções adequadas.
- Manifest e ícones mantidos para instalação como PWA.
- Nomenclatura visível permanece apenas como Metas.
- Ajustes extras de responsividade e tamanho de fontes no celular.
