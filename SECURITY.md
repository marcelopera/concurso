# Segurança

O sistema foi projetado para uso local por uma pessoa e não tem autenticação. Não publique o servidor na internet nem use `--host 0.0.0.0` em rede não confiável. O Compose liga a porta apenas ao endereço local. Os PDFs são resolvidos dentro da biblioteca configurada, montada somente para leitura. A política CSP permite estilos inline porque a interface e o Excalidraw os utilizam.

Não inclua bancos pessoais, PDFs ou credenciais em issues. Relate vulnerabilidades ao proprietário de forma privada pelo mecanismo de reporte de segurança do GitHub, se disponível.
