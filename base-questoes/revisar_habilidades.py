import json
from pathlib import Path
RUN=Path(__file__).resolve().parent/'execucoes/2026-10-29'
rows=[]
def add(did,num,disc,subject,skills):
    rows.append({'documento_id':did,'numero_original':num,'classificacoes':[{'disciplina':disc,'assunto':subject,'subassunto':None,'papel':'central','trecho_evidencia':skills[0][3],'origem':'leitura_individual_coordenador','confianca':'alta'}],'habilidades':[{'descricao_operacional':desc,'acao':action,'objeto_conhecimento':obj,'tipo_demanda':'conceitual' if num!='D1' else 'discursiva','papel':'central','trecho_evidencia':evidence,'origem':'leitura_individual_coordenador','confianca':'alta'} for desc,action,obj,evidence in skills]})
add('doc_97655bcdd13752ea40eb','D1','Administração pública','Projetos, programas e parcerias público-privadas',[
    ('Identificar exemplo real de parceria público-privada celebrada segundo a Lei 11.079/2004.','identificar','Parcerias público-privadas','Cite o nome de 01 (um) projeto real'),
    ('Distinguir projeto de programa segundo o PMBOK e justificar a classificação de um exemplo.','distinguir','Projetos e programas no PMBOK','Explique, segundo o PMBOK, 6ª Edição'),
    ('Explicar a finalidade do FACILITARS e citar dois de seus objetivos.','explicar','FACILITARS','explique qual a finalidade do FACILITARS')])
add('doc_0f507fed95bdb203fb43','31','Administração pública','Capacidade estatal e implementação de políticas públicas',[
    ('Avaliar se a capacidade administrativa estatal é suficiente para alcançar objetivos de políticas públicas.','avaliar','Capacidade administrativa e resultados de políticas públicas','A capacidade administrativa do Estado para formular e')])
add('doc_f7b93f5f3007eed1d281','31','Contabilidade geral','Elementos das demonstrações contábeis',[
    ('Relacionar definições do CPC 00 aos elementos ativo, passivo, patrimônio líquido, receita e despesa.','relacionar','Elementos das demonstrações contábeis','patrimônio líquido')])
(RUN/'lotes/zz_correcao_coordenador.enriquecimento.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
print('Três classificações revisadas individualmente.')
