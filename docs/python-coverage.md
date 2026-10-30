# Cobertura de código Python

A CI mede cobertura de linhas e desvios (`branch = True`) nas árvores completas de contratos, pipeline e backend de estudo. O limiar global de **54%** está em `.coveragerc`; ele exige avanço sobre a baseline ampla de `main` e mantém todos os módulos de negócio no denominador. A CI calcula e aplica esse valor em Linux, Windows e macOS. Cada execução publica JSON e Markdown com a cobertura por arquivo, sem conteúdo dos catálogos ou das fixtures.

A baseline abaixo foi medida em `main` no commit `01a0115966979d1426561d068989a0ab2574405f`, com 3 testes de arquitetura, 8 do pipeline e 35 do backend aprovados; os cinco testes de mapeamento dependentes do catálogo privado foram ignorados naquela versão. A cobertura combinada foi **52,1%** (56,7% das linhas e 39,7% dos desvios). O resumo por pacote foi: contratos 85,4%, backend 65,9% e pipeline 40,4%. O teste sintético desta issue elevou o resultado local combinado para 56,9%; o mapeador passou de 9,5% para 75,9% e o serviço de aulas de 45,1% para 53,8%.

| Módulo em `main` | Statements | Linhas | Desvios | Combinada |
|---|---:|---:|---:|---:|
| `packages/contracts/src/concurso_contracts/__init__.py` | 5 | 80,0% | 50,0% | 71,4% |
| `packages/contracts/src/concurso_contracts/catalog/contrato.py` | 28 | 96,4% | 90,0% | 94,7% |
| `packages/contracts/src/concurso_contracts/catalog/criar_demo.py` | 43 | 81,4% | 75,0% | 80,4% |
| `packages/estudo/backend/src/estudo/__main__.py` | 57 | 0,0% | 0,0% | 0,0% |
| `packages/estudo/backend/src/estudo/api/http.py` | 246 | 84,1% | 67,2% | 80,9% |
| `packages/estudo/backend/src/estudo/app.py` | 72 | 91,7% | 50,0% | 88,5% |
| `packages/estudo/backend/src/estudo/config.py` | 22 | 100,0% | 100,0% | 100,0% |
| `packages/estudo/backend/src/estudo/db/backup.py` | 23 | 78,3% | 50,0% | 74,1% |
| `packages/estudo/backend/src/estudo/db/connections.py` | 27 | 96,3% | 50,0% | 93,1% |
| `packages/estudo/backend/src/estudo/db/migrations/__init__.py` | 33 | 93,9% | 85,7% | 91,5% |
| `packages/estudo/backend/src/estudo/domain.py` | 34 | 79,4% | 60,0% | 75,0% |
| `packages/estudo/backend/src/estudo/errors.py` | 4 | 100,0% | 100,0% | 100,0% |
| `packages/estudo/backend/src/estudo/initialization.py` | 40 | 35,0% | 25,0% | 32,1% |
| `packages/estudo/backend/src/estudo/mapping/__main__.py` | 230 | 13,5% | 0,9% | 9,5% |
| `packages/estudo/backend/src/estudo/mapping/rules.py` | 146 | 80,1% | 8,3% | 70,0% |
| `packages/estudo/backend/src/estudo/plans.py` | 75 | 76,0% | 64,6% | 71,5% |
| `packages/estudo/backend/src/estudo/repositories/catalog.py` | 79 | 82,3% | 64,3% | 77,6% |
| `packages/estudo/backend/src/estudo/repositories/lessons.py` | 46 | 69,6% | 100,0% | 69,6% |
| `packages/estudo/backend/src/estudo/repositories/plans.py` | 48 | 100,0% | 100,0% | 100,0% |
| `packages/estudo/backend/src/estudo/repositories/profiles.py` | 55 | 92,7% | 83,3% | 91,8% |
| `packages/estudo/backend/src/estudo/repositories/question_links.py` | 63 | 85,7% | 81,8% | 84,7% |
| `packages/estudo/backend/src/estudo/repositories/sessions.py` | 48 | 97,9% | 100,0% | 97,9% |
| `packages/estudo/backend/src/estudo/services/catalog.py` | 76 | 69,7% | 54,5% | 66,3% |
| `packages/estudo/backend/src/estudo/services/lessons.py` | 138 | 47,1% | 38,6% | 45,1% |
| `packages/estudo/backend/src/estudo/services/plans.py` | 133 | 91,0% | 81,8% | 88,7% |
| `packages/estudo/backend/src/estudo/services/profiles.py` | 27 | 96,3% | 90,0% | 94,6% |
| `packages/estudo/backend/src/estudo/services/selection.py` | 21 | 100,0% | 100,0% | 100,0% |
| `packages/estudo/backend/src/estudo/services/sessions.py` | 182 | 87,9% | 71,7% | 83,9% |
| `packages/pipeline/src/concurso_pipeline/__main__.py` | 49 | 71,4% | 85,0% | 75,4% |
| `packages/pipeline/src/concurso_pipeline/common/__init__.py` | 11 | 100,0% | 100,0% | 100,0% |
| `packages/pipeline/src/concurso_pipeline/common/ids.py` | 6 | 100,0% | 100,0% | 100,0% |
| `packages/pipeline/src/concurso_pipeline/common/io.py` | 18 | 100,0% | 100,0% | 100,0% |
| `packages/pipeline/src/concurso_pipeline/common/paths.py` | 7 | 100,0% | 100,0% | 100,0% |
| `packages/pipeline/src/concurso_pipeline/common/text.py` | 19 | 94,7% | 100,0% | 95,2% |
| `packages/pipeline/src/concurso_pipeline/config.py` | 45 | 100,0% | 100,0% | 100,0% |
| `packages/pipeline/src/concurso_pipeline/extractors/__init__.py` | 2 | 100,0% | 100,0% | 100,0% |
| `packages/pipeline/src/concurso_pipeline/extractors/cebraspe_editais.py` | 297 | 0,0% | 0,0% | 0,0% |
| `packages/pipeline/src/concurso_pipeline/extractors/cebraspe_fundatec.py` | 218 | 74,3% | 58,0% | 68,8% |
| `packages/pipeline/src/concurso_pipeline/extractors/fcc_esaf_vunesp.py` | 171 | 73,7% | 56,0% | 67,8% |
| `packages/pipeline/src/concurso_pipeline/extractors/fcc_vunesp_editais.py` | 242 | 0,0% | 0,0% | 0,0% |
| `packages/pipeline/src/concurso_pipeline/extractors/fgv.py` | 196 | 68,9% | 53,2% | 63,8% |
| `packages/pipeline/src/concurso_pipeline/extractors/fgv_editais.py` | 256 | 0,0% | 0,0% | 0,0% |
| `packages/pipeline/src/concurso_pipeline/stages/cache.py` | 54 | 96,3% | 81,8% | 92,1% |
| `packages/pipeline/src/concurso_pipeline/stages/consolidate.py` | 270 | 58,1% | 39,7% | 52,0% |
| `packages/pipeline/src/concurso_pipeline/stages/gabaritos.py` | 108 | 0,0% | 0,0% | 0,0% |
| `packages/pipeline/src/concurso_pipeline/stages/index.py` | 26 | 88,5% | 75,0% | 86,7% |
| `packages/pipeline/src/concurso_pipeline/stages/render.py` | 22 | 0,0% | 0,0% | 0,0% |
| `packages/pipeline/src/concurso_pipeline/stages/repair_ce.py` | 74 | 83,8% | 78,1% | 82,1% |
| `packages/pipeline/src/concurso_pipeline/stages/review.py` | 77 | 80,5% | 69,2% | 76,0% |
| `packages/pipeline/src/concurso_pipeline/stages/validate.py` | 42 | 90,5% | 80,8% | 86,8% |

O artefato atual por sistema operacional mostra o resultado corrente por módulo; a tabela acima permanece como referência auditável da medição inicial. Os módulos sem cobertura não foram removidos do cálculo para elevar a porcentagem.
