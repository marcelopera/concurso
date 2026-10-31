PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS execucoes(execucao_id TEXT PRIMARY KEY,data_inicio TEXT,contrato_versao TEXT,metadados_json TEXT);
CREATE TABLE IF NOT EXISTS schema_meta(versao INTEGER NOT NULL,execucao_id TEXT NOT NULL,origem TEXT NOT NULL,gerado_em TEXT NOT NULL,commit_origem TEXT NOT NULL,hash_fontes TEXT NOT NULL,fontes_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documentos(documento_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL UNIQUE,tipo TEXT NOT NULL,banca TEXT,concurso TEXT,titulo TEXT,nome TEXT,arquivo_local TEXT NOT NULL,paginas INTEGER,url_fonte TEXT,metadados_json TEXT);
CREATE TABLE IF NOT EXISTS provas(prova_id TEXT PRIMARY KEY,documento_id TEXT NOT NULL REFERENCES documentos(documento_id),banca TEXT,concurso TEXT,titulo TEXT,caderno TEXT,metadados_json TEXT);
CREATE TABLE IF NOT EXISTS questoes(questao_id TEXT PRIMARY KEY,formato TEXT,enunciado_original TEXT NOT NULL,texto_para_busca TEXT,hash_texto TEXT NOT NULL,qualidade TEXT,registro_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ocorrencias(ocorrencia_id TEXT PRIMARY KEY,questao_id TEXT NOT NULL REFERENCES questoes(questao_id),prova_id TEXT NOT NULL REFERENCES provas(prova_id),documento_id TEXT NOT NULL REFERENCES documentos(documento_id),numero_original TEXT,bloco_original TEXT,disciplina_original TEXT,paginas_json TEXT,regioes_json TEXT,status_extracao TEXT,alertas_json TEXT,metodo_extracao TEXT,agente TEXT,execucao_id TEXT REFERENCES execucoes(execucao_id));
CREATE INDEX IF NOT EXISTS ix_ocorrencias_prova_numero ON ocorrencias(prova_id,numero_original);
CREATE TABLE IF NOT EXISTS alternativas(alternativa_id TEXT PRIMARY KEY,questao_id TEXT NOT NULL REFERENCES questoes(questao_id),rotulo TEXT,ordem INTEGER,texto_original TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contextos(contexto_id TEXT PRIMARY KEY,texto_original TEXT NOT NULL,registro_json TEXT);
CREATE TABLE IF NOT EXISTS questao_contexto(questao_id TEXT REFERENCES questoes(questao_id),contexto_id TEXT REFERENCES contextos(contexto_id),ordem INTEGER,PRIMARY KEY(questao_id,contexto_id));
CREATE TABLE IF NOT EXISTS fontes_visuais(visual_id TEXT PRIMARY KEY,documento_id TEXT REFERENCES documentos(documento_id),pagina INTEGER,arquivo_imagem TEXT,largura_pt REAL,altura_pt REAL,UNIQUE(documento_id,pagina));
CREATE TABLE IF NOT EXISTS classificacoes(classificacao_id TEXT PRIMARY KEY,questao_id TEXT REFERENCES questoes(questao_id),disciplina TEXT,assunto TEXT,subassunto TEXT,papel TEXT,trecho_evidencia TEXT,origem TEXT,confianca TEXT,status_revisao TEXT,registro_json TEXT);
CREATE TABLE IF NOT EXISTS habilidades(habilidade_id TEXT PRIMARY KEY,descricao_operacional TEXT NOT NULL,acao TEXT,objeto_conhecimento TEXT,tipo_demanda TEXT,versao_definicao TEXT,status_revisao TEXT);
CREATE TABLE IF NOT EXISTS questao_habilidade(questao_habilidade_id TEXT PRIMARY KEY,questao_id TEXT REFERENCES questoes(questao_id),habilidade_id TEXT REFERENCES habilidades(habilidade_id),papel TEXT,trecho_evidencia TEXT,origem TEXT,confianca TEXT,status_revisao TEXT,registro_json TEXT);
CREATE TABLE IF NOT EXISTS gabaritos(gabarito_registro_id TEXT PRIMARY KEY,documento_id TEXT REFERENCES documentos(documento_id),concurso TEXT,numero_original TEXT,resposta_publicada TEXT,situacao_item TEXT,natureza_gabarito TEXT,versao_caderno TEXT,escopo_original TEXT,paginas_json TEXT,regioes_json TEXT,registro_json TEXT);
CREATE INDEX IF NOT EXISTS ix_gabaritos_concurso_numero ON gabaritos(concurso,numero_original);
CREATE TABLE IF NOT EXISTS ocorrencia_gabarito(ocorrencia_id TEXT REFERENCES ocorrencias(ocorrencia_id),gabarito_registro_id TEXT REFERENCES gabaritos(gabarito_registro_id),status_associacao TEXT,regra_associacao TEXT,PRIMARY KEY(ocorrencia_id,gabarito_registro_id));
CREATE TABLE IF NOT EXISTS topicos(topico_id TEXT PRIMARY KEY,documento_id TEXT REFERENCES documentos(documento_id),topico_pai_id TEXT REFERENCES topicos(topico_id) DEFERRABLE INITIALLY DEFERRED,numero_original TEXT,ordem_original INTEGER,texto_original TEXT NOT NULL,texto_para_busca TEXT,disciplina_original TEXT,caminho_json TEXT,escopo_cargos_json TEXT,escopo_especialidades_json TEXT,bloco TEXT,tipo_publicacao TEXT,estado_na_versao TEXT,paginas_json TEXT,regioes_json TEXT,status_extracao TEXT,alertas_json TEXT,registro_json TEXT);
CREATE TABLE IF NOT EXISTS associacoes_topico_questao(associacao_id TEXT PRIMARY KEY,topico_id TEXT REFERENCES topicos(topico_id),questao_id TEXT REFERENCES questoes(questao_id),tipo_relacao TEXT,score REAL,trecho_questao_evidencia TEXT,trecho_topico_evidencia TEXT,justificativa TEXT,metodo TEXT,confianca TEXT,status_revisao TEXT);
CREATE TABLE IF NOT EXISTS pendencias(pendencia_id TEXT PRIMARY KEY,tipo TEXT,entidade_id TEXT,documento_id TEXT REFERENCES documentos(documento_id),descricao TEXT,status TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS questoes_fts USING fts5(questao_id UNINDEXED,texto,disciplina,assunto,tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS topicos_fts USING fts5(topico_id UNINDEXED,texto,disciplina,tokenize='unicode61 remove_diacritics 2');
CREATE VIEW IF NOT EXISTS vw_questoes AS SELECT q.questao_id,o.ocorrencia_id,d.banca,d.concurso,d.titulo,o.numero_original,o.bloco_original,o.disciplina_original,q.formato,q.enunciado_original,q.texto_para_busca,o.status_extracao,o.alertas_json,o.paginas_json,d.arquivo_local FROM questoes q JOIN ocorrencias o USING(questao_id) JOIN documentos d USING(documento_id);
CREATE VIEW IF NOT EXISTS vw_gabaritos_associados AS SELECT og.ocorrencia_id,g.*,og.status_associacao,og.regra_associacao FROM ocorrencia_gabarito og JOIN gabaritos g USING(gabarito_registro_id);
CREATE VIEW IF NOT EXISTS vw_gabaritos_referencia AS
WITH fontes AS (
    SELECT *,max(CASE WHEN natureza_gabarito='definitivo' THEN 1 ELSE 0 END)
    OVER(PARTITION BY ocorrencia_id) AS tem_definitivo FROM vw_gabaritos_associados
),preferidas AS (
    SELECT * FROM fontes WHERE tem_definitivo=0 OR natureza_gabarito='definitivo'
)
SELECT ocorrencia_id,
CASE WHEN count(DISTINCT resposta_publicada || '|' || situacao_item)=1 THEN min(resposta_publicada) END AS resposta_referencia,
CASE WHEN count(DISTINCT resposta_publicada || '|' || situacao_item)=1 THEN min(situacao_item) END AS situacao_referencia,
CASE WHEN count(DISTINCT resposta_publicada || '|' || situacao_item)>1 THEN 'divergente' ELSE 'concordante' END AS estado,
max(tem_definitivo) AS possui_publicacao_definitiva
FROM preferidas GROUP BY ocorrencia_id;
