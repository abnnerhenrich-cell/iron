# IRON — melhorias desta versão

Esta versão mantém o fluxo original do IRON: ciclos, metas personalizadas por membro, entregas com comprovantes e aprovação administrativa.

## Interface e usabilidade
- Redesign completo em preto/prata, com melhor hierarquia visual, espaçamento e contraste.
- Layout responsivo revisado para desktop e celular.
- Barra superior e navegação administrativa mais limpas.
- Navegação inferior mobile otimizada.
- Cards, tabelas, formulários, botões, estados e mensagens padronizados.
- Mensagens do sistema fecháveis e com desaparecimento automático.
- Busca instantânea de membros por nome ou e-mail.
- Status do histórico traduzidos para português.
- Área de entrega mais clara, com controles de quantidade e botão com estado de envio.

## Funcionalidade e robustez
- Foto do membro agora aparece corretamente nas telas administrativas que a utilizam.
- O sistema deixa de carregar o binário inteiro da foto do usuário em todas as páginas, melhorando desempenho.
- Histórico pessoal reconhece comprovantes armazenados em lotes e permite abrir até 3 imagens.
- Validação no servidor impede entregar quantidade acima do saldo disponível da meta.
- Campo de quantidade também recebe limite máximo no navegador.
- Revisão administrativa só altera entregas que ainda estejam pendentes, evitando reprocessamento acidental.
- Acesso à foto de perfil foi restringido: membro vê a própria foto; administradores podem ver fotos dos membros.
- Cookies de sessão receberam configurações mais seguras.

## Validações executadas
- `app.py` compilado com sucesso pelo Python.
- Todos os templates Jinja foram compilados/validados sem erro de sintaxe.
