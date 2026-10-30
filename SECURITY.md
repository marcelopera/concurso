# Segurança

O sistema foi projetado para uso local por uma pessoa e não tem autenticação. Não publique o servidor na internet nem use `--host 0.0.0.0` em rede não confiável. O Compose liga a porta apenas ao endereço local. Os PDFs são resolvidos dentro da biblioteca configurada, montada somente para leitura. A política CSP permite estilos inline porque a interface e o Excalidraw os utilizam.

Não inclua bancos pessoais, PDFs ou credenciais em issues. Relate vulnerabilidades ao proprietário de forma privada pelo mecanismo de reporte de segurança do GitHub, se disponível.

A API verifica Host/Origin locais e isola perfis por requisição; isso não equivale a autenticação. Qualquer processo que tenha acesso local ao servidor pode usar a API. A escolha de `--host 0.0.0.0` amplia a superfície acessível, mesmo com essas verificações, e não é um modo de hospedagem suportado.

O workflow de segurança executa auditoria das dependências de produção, CodeQL, Trivy na imagem final e Gitleaks nas alterações. Os scans são verificações automatizadas; recursos como proteção de branch e push protection precisam ser habilitados pelo proprietário nas configurações do GitHub.
