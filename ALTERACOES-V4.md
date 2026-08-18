# IRON V4 — HUD + PWA

## Interface
- Corrigido o card da meta ativa que colava o rótulo ao título.
- HUD defensivo contra nomes e títulos longos em desktop e celular.
- Nomenclatura visual `Ciclos` removida e substituída por `Metas`.
- Sidebar administrativa identificada como `PAINEL DA HIERARQUIA`.
- Mantidos os nomes internos de rotas/tabela `cycles` para preservar compatibilidade com o banco existente.

## Aplicativo instalável (PWA)
- Manifesto web com nome IRON, cores e ícones próprios.
- Favicon na aba do navegador.
- Apple Touch Icon para iPhone/iPad.
- Ícones 192x192 e 512x512 para Android/desktop.
- Service Worker com cache somente de arquivos estáticos.
- Botão `Instalar IRON` quando o navegador oferece instalação.
- No iOS, o botão abre orientação para `Compartilhar > Adicionar à Tela de Início`.
- A interface de instalação desaparece quando o app já está instalado.

## Validação
- app.py compilado com sucesso.
- 18 templates Jinja validados sem erro de sintaxe.
