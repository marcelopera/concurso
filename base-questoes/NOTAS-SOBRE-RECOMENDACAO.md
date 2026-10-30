# Notas anteriores sobre recomendação e reforço

Estado: referência histórica de planejamento, fora do esquema da base de questões.

Após o refinamento de 29/10/2026, a recomendação e o acompanhamento do aluno pertencem a outra estrutura. As sugestões abaixo não são requisitos da extração nem definem a arquitetura dessa estrutura. A definição vigente das habilidades avaliadas está em PROPOSTA-DA-BASE.md.

## Informações opcionais para uma etapa posterior

- Histórico de tentativas, acertos, tempo e revisões do usuário: necessário desde o início se o objetivo incluir recomendação adaptativa e identificação de pontos fracos, conforme a extensão proposta abaixo.
- Estimativa de dificuldade, sempre marcada como estimativa; dificuldade empírica depende de dados reais de resposta.
- Resoluções e comentários pedagógicos gerados, separados dos gabaritos oficiais.
- Análise de atualização normativa, com fontes e data de verificação próprias.

Essas informações não são necessárias para a transcrição, a indexação e o match inicial e não serão fabricadas durante a extração.

## Extensão proposta: recomendação adaptativa e reforço

Estado: proposta para avaliação, decorrente do objetivo de recomendar questões e identificar pontos fracos. Não implementada e sem extração iniciada.

O catálogo de questões e o match com editais permitem selecionar conteúdo relevante. Para recomendar de acordo com o aprendizado de uma pessoa, será necessário registrar suas interações e manter estimativas de aprendizagem por habilidade, com incerteza explícita.

### Habilidades observáveis

Além dos assuntos e tópicos do edital, representar habilidades como ações avaliáveis: identificar um estágio da despesa, distinguir dois conceitos, interpretar uma tabela ou realizar um cálculo específico. Relacionar questão e habilidade em uma estrutura muitos-para-muitos.

Campos adicionais: `habilidade_id`, `descricao_operacional`, `conceitos_ids`, `tipo_demanda`, `prerequisitos_ids`, `origem_vinculo`, `evidencia`, `status_revisao`.

As relações de pré-requisito são hipóteses de conteúdo passíveis de revisão. A ocorrência de um erro não comprova uma deficiência em todos os conceitos relacionados à questão.

### Perfil e objetivo de estudo

Campos: `usuario_id`, `edital_alvo_id`, `cargo_alvo_id`, `especialidade_alvo_id`, `data_prova_alvo`, `disponibilidade_estudo`, `preferencias_formato`, `estrategia_recomendacao`.

Prioridades explícitas do edital, número de questões e pesos só terão origem documental ou configuração declarada pelo usuário. Frequência no acervo disponível é uma estatística descritiva desse acervo, não uma estimativa automática da probabilidade de cobrança futura.

### Eventos de estudo e tentativas

Guardar o histórico de eventos, sem substituir tentativas anteriores por um placar acumulado.

Campos: `evento_id`, `usuario_id`, `sessao_id`, `ocorrencia_id`, `questao_id`, `recomendacao_id`, `evento_tipo`, `data_hora`, `resposta_dada`, `resultado_correcao`, `gabarito_versao_id`, `tempo_ativo_segundos`, `metodo_medicao_tempo`, `uso_consulta`, `uso_dica`, `gabarito_exposto_antes`, `feedback_exposto_antes`, `questao_vista_antes`, `tentativa_numero`, `grupo_duplicidade`, `confianca_declarada`, `motivo_erro_declarado`.

Eventos previstos: recomendada, apresentada, iniciada, respondida, pulada, abandonada, dica consultada e feedback visualizado. Não tratar uma questão apresentada ou uma omissão como resposta errada.

Confiança, motivo de erro e consultas podem ser desconhecidos. Não exigir autorrelato em toda questão nem inferir automaticamente que tempo longo significa dificuldade conceitual. Separar tempo ativo de duração total quando isso for tecnicamente mensurável.

Uma nova tentativa na mesma questão ou numa cópia equivalente não oferece a mesma evidência de transferência que uma questão inédita. Registrar exposições anteriores e uso de ajuda.

### Estado de aprendizagem derivado

Campos: `usuario_id`, `habilidade_id`, `modelo_estado_versao`, `data_atualizacao`, `estimativa_desempenho`, `incerteza_estimativa`, `estado_descritivo`, `tentativas_validas`, `questoes_distintas`, `familias_distintas`, `acertos_primeira_tentativa`, `ultimas_evidencias`, `ultima_pratica`, `proxima_revisao_sugerida`.

Estados descritivos iniciais sugeridos: sem evidência suficiente, em aprendizagem, desempenho instável e desempenho consistente. Esses estados são operacionais, não diagnósticos clínicos ou garantias de domínio.

Separar incerteza da extração, incerteza do vínculo questão-habilidade e incerteza da estimativa sobre o aluno. Definir e validar critérios antes de apresentar percentuais como probabilidades calibradas.

Não atualizar todas as habilidades de uma questão multiconceitual igualmente a partir de um único erro. Uma recomendação diagnóstica poderá buscar outra questão que isole melhor a habilidade suspeita.

### Erros e intervenções

Campos: `hipotese_erro_id`, `tentativa_id`, `habilidade_id`, `alternativa_escolhida`, `categoria_erro`, `justificativa_curta`, `origem_hipotese`, `grau_confianca`, `status_validacao`.

Categorias possíveis: conceito, procedimento, interpretação, cálculo e desatenção declarada. Essas categorias não serão atribuídas com certeza apenas pela alternativa marcada. Distratores poderão receber hipóteses explicativas revisáveis, separadas do texto oficial.

Registrar intervenções de reforço como revisão conceitual, exemplo resolvido, questão de pré-requisito, nova questão do mesmo conceito e revisão após intervalo. Recursos ou resoluções gerados precisam de indicação de autoria e revisão, sem se passarem por comentários oficiais.

### Decisões de recomendação

Campos: `recomendacao_id`, `usuario_id`, `data_hora`, `objetivo`, `questao_id`, `habilidades_alvo`, `edital_alvo_id`, `motivo_legivel`, `versao_politica`, `componentes_prioridade`, `posicao`, `resultado_exposicao`.

Objetivos possíveis: diagnóstico inicial, reforço, revisão espaçada, conteúdo ainda não praticado, verificação de transferência e simulado.

Considerar relevância para o edital, evidência de dificuldade, tempo desde a prática, incerteza sobre a habilidade, diversidade de questões e disponibilidade de questões confiáveis. Não restringir permanentemente a prática aos erros conhecidos nem recomendar somente cópias do mesmo item.

Priorizar itens com extração revisada, vínculo temático confiável e gabarito utilizável. Questões anuladas, ambíguas ou com conflito de gabarito não devem contar como evidência normal de aprendizagem.

### Validação do sistema

- Começar com critérios transparentes e diagnóstico de cobertura, sem depender de modelos complexos treinados com poucos dados pessoais.
- Avaliar retenção após intervalos e desempenho em questões distintas, além do acerto imediato após feedback.
- Medir se as recomendações ajudam a cobrir o edital e a melhorar resultados em questões ainda não vistas.
- Preservar motivos e versões das recomendações para auditoria e comparação de políticas.
- Tratar diagnóstico inicial e busca de evidência nova como componentes permanentes; seleção adaptativa pode deixar habilidades sem observações se o sistema consultar apenas o que já considera fraco.
- Recalcular resultados afetados por revisão do gabarito ou correção da extração, preservando as respostas originais do usuário.

Referências consultadas para a proposta:

- Corbett e Anderson, Knowledge Tracing (1995): https://perso.liris.cnrs.fr/pierre-antoine.champin/2014/m2iade-ia2/_static/893CorbettAnderson1995.pdf
- IES/What Works Clearinghouse, Organizing Instruction and Study to Improve Student Learning: https://ies.ed.gov/ncee/wwc/PracticeGuide/1
- EDM 2025, representação de componentes de conhecimento e associação entre itens e habilidades: https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.170/
