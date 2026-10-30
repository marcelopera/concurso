# Sistema de estudo

Consulte o [README principal](../README.md) para instalação, execução e testes. O aplicativo salva o progresso em `dados/estudo.sqlite` e mantém o catálogo em somente leitura. Faça backup do volume Docker `estudo-dados` ou dos bancos em `dados/` antes de migrar ou restaurar o ambiente.

Os PDFs são opcionais e ficam fora da imagem Docker. Caminhos legados do catálogo são resolvidos sob `BIBLIOTECA_DIR`; arquivos fora dessa pasta não são servidos. O plano e seus vínculos podem ser instalados em um banco novo com `python scripts/preparar_container.py`.
