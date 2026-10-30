# Sistema de estudo

Consulte o [README principal](../README.md) para instalação, execução e testes. O aplicativo salva o progresso em `dados/estudo.sqlite` e mantém o catálogo em somente leitura. Faça backup do volume Docker `estudo-dados` ou dos bancos em `dados/` antes de migrar ou restaurar o ambiente.

Os PDFs são opcionais e ficam fora da imagem Docker. Caminhos legados do catálogo são resolvidos sob `BIBLIOTECA_DIR`; arquivos fora dessa pasta não são servidos. Use `python scripts/inicializar.py` e `python -m estudo`, como no README principal; a inicialização preserva bancos existentes. `preparar_container.py` continua sendo um passo interno da imagem Docker.
