"""Build the A01 curriculum from contiguous, fully covered official syllabus excerpts."""

import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://portal.fazenda.sp.gov.br/servicos/concursos/"
PDF_URL = BASE_URL + "Documents/EDITAL%20N%C2%BA%2001-2026%20-%20ABERTURA%20DAS%20INCRI%C3%87%C3%95ES%20APOFP.pdf"

# Each start marker partitions the source: no phrase can fall between units.
# Titles and groupings are study suggestions; excerpts remain the official source.
SPECS = [
    (
        "adm",
        "Administração Geral, Administração Pública e Auditoria Governamental",
        8,
        1,
        """
Fundamentos|Teorias administrativas e PODC|Administração Geral e Pública
Fundamentos|Estruturas e processo decisório|Estrutura Organizacional
Estratégia e gestão|Planejamento estratégico: SWOT, Porter, cadeia de valor e OKR|Planejamento Estratégico
Estratégia e gestão|Gestão por processos e projetos: BPM, PMBOK, Scrum e Kanban|Gestão por Processos
Estratégia e gestão|Comportamento organizacional e gestão de pessoas|Comportamento Organizacional
Gestão pública|Modelos de gestão, governança, accountability, LAI e LGPD|Modelos de Gestão Pública
Gestão pública|Parcerias, terceiro setor, políticas públicas e avaliação|Parcerias com o Setor Privado
Auditoria e controle|Tipos de auditoria e instrumentos de fiscalização|Auditoria Governamental e Controle Interno
Auditoria e controle|COSO, ISO 31000 e modelo das Três Linhas|Modelos de Gestão de Riscos
Auditoria e controle|IPPF, NBC TA, NBASP, IA-CM e controle interno|Normas e Modelos de Capacidade
Auditoria e controle|Integridade, anticorrupção, ESG, ouvidoria e resposta ao controle|Integridade e Ética
""",
    ),
    (
        "da",
        "Direito Administrativo",
        10,
        1,
        """
Fundamentos|Fontes, Estado, órgãos, organização e princípios|Teoria Geral
Atos e poderes|Atos: elementos, atributos, espécies e extinção|Atos Administrativos e Poderes
Atos e poderes|Convalidação, decadência e poderes administrativos|Convalidação
Agentes e regime estadual|Agentes, regime constitucional, PAD e Decreto 69.122/2024|Agentes Públicos e Regime Estatutário
Contratações e serviços|Lei 14.133/2021 e contratos administrativos|Licitações, Contratos e Serviços Públicos
Contratações e serviços|Serviços, parcerias, bens e responsabilidade civil|Serviços Públicos e Formas de Parceria
Controle e integridade|Controle e improbidade: Leis 8.429/1992 e 14.230/2021|Controle da Administração
Controle e integridade|LAI, LGPD, dados abertos, anticorrupção e Estatuto paulista|Integridade, Transparência e Governança
""",
    ),
    (
        "dc",
        "Direito Constitucional",
        10,
        1,
        """
Constituição e direitos|Teoria da Constituição, eficácia, constituinte e hermenêutica|Teoria Geral da Constituição
Constituição e direitos|Direitos fundamentais e remédios constitucionais|Direitos e Garantias Fundamentais
Estado e poderes|Federação, administração, poderes e fiscalização|Organização Político
Finanças constitucionais|Finanças e orçamento: arts. 163 a 169|Finanças Públicas e Orçamentos
Finanças constitucionais|Tributos, repartição e EC 132/2023|Sistema Tributário Nacional
Controle e ordens constitucionais|Controle de constitucionalidade|Controle de Constitucionalidade
Controle e ordens constitucionais|Ordem econômica, ordem social e Constituição de São Paulo|Ordem Econômica e Financeira
""",
    ),
    (
        "eco",
        "Economia",
        4,
        1,
        """
Microeconomia|Oferta, demanda, elasticidades e estruturas de mercado|Teoria Microeconômica
Microeconomia|Bem-estar, falhas de mercado, escolha pública e tributação|Economia do bem
Macroeconomia|Renda, crescimento, políticas e contas nacionais|Teoria Macroeconômica
Macroeconomia|Inflação, trabalho e modelos IS-LM e Mundell-Fleming|Curva de Phillips
Macroeconomia|Câmbio, economia aberta e efeitos fiscais de variáveis macro|Regimes e taxas de câmbio
Avaliação de projetos|Investimentos, etapas, TMA e indicadores econômicos|Avaliação econômica de projetos
Avaliação de projetos|Sensibilidade, risco, projetos sociais, ETTJ, duration e VaR|análise de sensibilidade
""",
    ),
    (
        "por",
        "Língua Portuguesa",
        10,
        1,
        """
Texto e semântica|Ortografia, acentuação e crase|Ortografia
Texto e semântica|Interpretação, contexto, discursos e figuras de linguagem|Compreensão
Gramática|Morfossintaxe, formação de palavras, sinonímia e antonímia|Morfossintaxe
Gramática|Pontuação, pronomes e concordância|Pontuação
Gramática|Flexões, vozes e correlação de tempos e modos|Flexão nominal
Gramática|Regência, coordenação, subordinação e conectivos|Regência nominal
""",
    ),
    (
        "mat",
        "Matemática Financeira / Estatística",
        6,
        1,
        """
Matemática financeira|Juros, taxas, equivalência e capitalização contínua|Matemática Financeira
Matemática financeira|Séries, descontos e sistemas de amortização|séries de pagamentos
Matemática financeira|Fluxo de caixa, valor presente, VPL e TIR|fluxo de caixa
Estatística descritiva|Variáveis, gráficos, medidas, outliers, covariância e correlação|Estatística:
Probabilidade|Probabilidade, Bayes e variáveis aleatórias|Probabilidades:
Probabilidade|Distribuições, TCL, esperança, variância e funções geradoras|distribuições de probabilidade
Inferência|Amostragem, tamanho de amostra e estimação|Inferência estatística
Inferência|Testes, erros, valor-p, poder e ANOVA|testes de hipóteses
Regressão e modelos|Regressão, validação, séries temporais e ARIMA|Regressão e predição
Regressão e modelos|Aprendizado e métricas de classificação e regressão|Modelagem estatística
Regressão e modelos|Algoritmos, agrupamentos, redução de dimensão e regularização|modelos supervisionados
""",
    ),
    (
        "afo",
        "Administração Financeira e Orçamentária",
        8,
        2,
        """
Classificações e créditos|Classificações, fontes e natureza da receita e despesa|Classificação da despesa
Classificações e créditos|Créditos, descentralização e emendas impositivas|Alterações orçamentárias
Execução orçamentária e financeira|Conta Única, contingenciamento, cronograma e DEA|Conta Única
Execução orçamentária e financeira|Estágios da despesa e receita, programação, RAP e suprimento|Empenho.
Planejamento e orçamento|Ciclo, conceitos e técnicas orçamentárias|Ciclo e processo orçamentário
Planejamento e orçamento|Princípios, execução, controle e desempenho|Princípios orçamentários
Planejamento e orçamento|Sistemas, estrutura programática, PPA, LDO, LOA e metas|Sistemas de administração
""",
    ),
    (
        "con",
        "Contabilidade Geral e Pública",
        8,
        2,
        """
Contabilidade pública|CASP, patrimônio, regimes e variações patrimoniais|Contabilidade Aplicada ao Setor Público
Contabilidade pública|Reconhecimento, mensuração, sistema e PCASP|Reconhecimento, mensuração
Contabilidade pública|MCASP, escrituração e integração da execução|Manual de Contabilidade
Demonstrações públicas|Balanços orçamentário, financeiro e patrimonial|Demonstrações Contábeis Aplicadas
Demonstrações públicas|DVP, DMPL, DFC e notas explicativas|Demonstração das Variações Patrimoniais
Contabilidade geral|Conceitos, patrimônio, equação e classes de contas|Contabilidade Geral
Contabilidade geral|Débito, crédito, partidas dobradas, regimes e resultado|Débito e crédito
""",
    ),
    (
        "df",
        "Direito Financeiro e Finanças Públicas",
        8,
        2,
        """
Bases e responsabilidade fiscal|Fontes, LRF, Lei 4.320 e normas constitucionais|Fontes e princípios
Bases e responsabilidade fiscal|PPA, LDO, LOA, ARO, crédito, dívida e regra de ouro|Disciplina constitucional do PPA
Despesa e orçamento|Pessoal, despesa continuada, geração e legalidade|Despesa com pessoal
Despesa e orçamento|Planejamento, controle, precatórios e processo orçamentário|Atividade financeira do Estado
Receita e federalismo|Receitas, renúncia, dívida ativa e ingressos|Conceito jurídico de receita
Receita e federalismo|Equalização, federalismo, repartição e transferências|Equalização fiscal
Resultados fiscais|Acima/abaixo da linha, déficit, NFSP e resultados fiscais|Critérios acima e abaixo da linha
""",
    ),
    (
        "dad",
        "Fluência de Dados",
        8,
        2,
        """
Fundamentos e arquitetura|Tipos de dados, ciclo da informação e CRISP-DM|Ciência de Dados:
Fundamentos e arquitetura|Big Data, arquiteturas, engenharia, preparação e qualidade|Big Data e Arquitetura
Bancos e análise|Bancos relacionais, NoSQL e SQL|Banco de dados:
Bancos e análise|Análise, mineração, ML, deep learning, PLN e IA generativa|Análise de dados:
Governança e proteção|Governança, responsabilidades, qualidade e ética em IA|Governança de Dados:
Governança e proteção|Segurança, riscos, acesso, anonimização e retenção|Segurança da Informação e Proteção de Dados:
Governança e proteção|Marco Civil, LGPD, Poder Público e incidentes|Conformidade legal e regulatória
""",
    ),
    (
        "a01",
        "A01 · Orçamento e Finanças Públicas",
        40,
        3,
        """
Créditos e alterações|Superávit financeiro e abertura de créditos adicionais|Apuração e utilização
Créditos e alterações|Remanejamentos e fontes para créditos|Remanejamentos
Créditos e alterações|Descentralização, emendas e tipos de empenho|Descentralização de créditos
Execução e fontes|Convênios, liquidação, pagamento, reforço e anulação|Execução orçamentária e financeira de convênios
Execução e fontes|Alteração, saldos, compatibilidade e controle das fontes|Alteração de fonte
Execução e fontes|Recursos vinculados, próprios, transferências e crédito|Recursos vinculados
Execução e fontes|Contingenciamento, bloqueios, cronograma e caixa|Contingenciamento
Execução e fontes|Limites de movimentação, empenho e pagamento|Limites de movimentação
Restos a pagar e encerramento|Bloqueio, cancelamento, pagamento e caixa por fonte|Bloqueio, desbloqueio
Restos a pagar e encerramento|Encerramento e inscrição de RAP processados e não processados|Encerramento do exercício
Gestão fiscal e recursos estaduais|LRF avançada, Lei 4.320 e normas constitucionais|Tópicos Avançados
Gestão fiscal e recursos estaduais|Movimentação e transferências entre Tesouro e entidades|Regras de movimentação
Repartição de receitas|Critérios, FPE, FPM e participação em IR, IPI, ITR, ICMS e IPVA|Critérios, bases
Repartição de receitas|Repartição federativa e modalidades de transferência|Repartição constitucional
Gestão fiscal e dívida|Controle, contas, transferências voluntárias e transparência|Controle e fiscalização
Gestão fiscal e dívida|Dívida, âncoras, sustentabilidade, perfil e garantias|Dinâmica da dívida
""",
    ),
]


def norm(text):
    text = re.sub(r"\s+", " ", text).strip()
    fixes = {
        "Centraliza ção": "Centralização",
        "racionalid ade": "racionalidade",
        "financiamen to": "financiamento",
        "Fiscal ização": "Fiscalização",
        "Administr ativos": "Administrativos",
        "Res ponsabilidades": "Responsabilidades",
        "R emédios": "Remédios",
        "Co ntrole": "Controle",
        "ac entuação": "acentuação",
        "Cré ditos": "Créditos",
        "Des pesas": "Despesas",
        "nature za": "natureza",
        "Mensura ção": "Mensuração",
        "orçame ntário": "orçamentário",
        "M CASP": "MCASP",
        "Bala nço": "Balanço",
        "Iniciati va": "Iniciativa",
        "Reparti ção": "Repartição",
        "Ap rendizado": "Aprendizado",
        "Conformid ade": "Conformidade",
        "e mpenho": "empenho",
        "lega is": "legais",
        "ent re": "entre",
        "distri buições": "distribuições",
        "R egressão": "Regressão",
        "M SE": "MSE",
        "v etores": "vetores",
        "u niformes": "uniformes",
        "funções geradoras de momentos": "funções geradoras de momentos",
    }
    for a, b in fixes.items():
        text = text.replace(a, b)
    # Word extraction sometimes inserts spaces before accented syllables.
    for a, b in [
        ("acentua ção", "acentuação"),
        ("Compreens ão", "Compreensão"),
        ("interpreta ção", "interpretação"),
        ("g êneros", "gêneros"),
        ("hist órico", "histórico"),
        ("conota ção", "conotação"),
        ("Sinon ímia", "Sinonímia"),
        ("anton ímia", "antonímia"),
        ("Concord ância", "Concordância"),
        ("concord ância", "concordância"),
        ("flex ão", "flexão"),
        ("Correla ção", "Correlação"),
        ("Reg ência", "Regência"),
        ("reg ência", "regência"),
        ("valor- p", "valor-p"),
        ("IA- CM", "IA-CM"),
        ("k - means", "k-means"),
        ("k- NN", "k-NN"),
        ("custo- benefício", "custo-benefício"),
    ]:
        text = text.replace(a, b)
    return text


def build():
    reader = PdfReader(ROOT / "fontes" / "edital-01-2026.pdf")
    pages = [norm(reader.pages[i].extract_text()) for i in range(30, 35)]
    text = " ".join(pages)
    headings = [s[1] for s in SPECS[:-1]] + ["A01: CONHECIMENTOS ESPECÍFICOS", "B02: CONHECIMENTOS ESPECÍFICOS"]
    offsets = [text.index(h) for h in headings]
    subjects = []
    lessons = []
    for n, (key, name, questions, weight, spec) in enumerate(SPECS):
        start = offsets[n] + len(headings[n])
        stop = offsets[n + 1]
        original = text[start:stop].strip()
        original = re.sub(r"PROVA 2\s*$", "", original).strip()
        if key == "a01":
            original = original[original.index("Apuração e utilização") :]
        rows = [line.split("|") for line in spec.strip().splitlines()]
        boundaries = [original.index(row[2]) for row in rows] + [len(original)]
        assert boundaries[0] == 0, (key, original[:80])
        assert boundaries == sorted(set(boundaries)), key
        groups = {}
        units = []
        for i, (topic, title, marker) in enumerate(rows):
            excerpt = original[boundaries[i] : boundaries[i + 1]].strip()
            topic_id = groups.setdefault(topic, f"apofp26_{key}_t{len(groups) + 1:02d}")
            unit = dict(
                lesson_id=f"apofp26_{key}_{i + 1:02d}",
                subject_id=f"apofp26_{key}",
                topic_id=topic_id,
                topic=topic,
                title=title,
                position=i + 1,
                source_excerpt=excerpt,
                source_offset=boundaries[i],
                minutes=63,
                source_url=PDF_URL,
                pages=[31 + j for j, p in enumerate(pages) if marker in p],
                exam="P2" if key == "a01" else "P1 / P3",
                checklist=[x.strip() for x in re.split(r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", excerpt) if x.strip()],
            )
            units.append(unit)
        assert norm(" ".join(u["source_excerpt"] for u in units)) == norm(original), key
        if key == "afo":
            units = units[4:] + units[:4]
        if key == "con":
            units = units[5:] + units[:5]
        for i, u in enumerate(units):
            u["study_order"] = i + 1
        lessons.extend(units)
        subjects.append(
            dict(
                subject_id=f"apofp26_{key}",
                key=key,
                name=name,
                questions=questions,
                weight=weight,
                points=questions * weight,
                exam="P2" if key == "a01" else "P1",
                source_text=original,
                lessons=units,
            )
        )
    # Interleave subjects while preserving their internal learning order.
    queues = {s["key"]: list(s["lessons"]) for s in subjects}
    cycle = ["afo", "df", "con", "dc", "a01", "adm", "da", "a01", "por", "mat", "dad", "eco"]
    ordered = []
    while any(queues.values()):
        for key in cycle:
            if not queues[key]:
                continue
            if key == "a01" and any(
                sum(u["subject_id"] == f"apofp26_{k}" for u in ordered) < 2 for k in ["afo", "df", "con"]
            ):
                continue
            ordered.append(queues[key].pop(0))
    first = date(2026, 10, 29)
    last_new = date(2026, 12, 10)
    exam = date(2026, 12, 20)
    sim = {"2026-11-21": "P1", "2026-11-22": "P2 + P3", "2026-12-12": "P1", "2026-12-13": "P2 + P3"}
    teaching = [
        first + timedelta(days=i)
        for i in range((last_new - first).days + 1)
        if (first + timedelta(days=i)).isoformat() not in sim
    ]
    days = []
    consumed = 0
    cases = [
        "Caso de orçamento: diagnosticar falha na execução e propor solução compatível com PPA, LDO e LOA.",
        "Caso de controle: identificar risco, evidência, controle e encaminhamento à auditoria.",
        "Caso contábil: distinguir efeitos orçamentários, financeiros e patrimoniais de uma operação.",
        "Caso de transparência e LGPD: conciliar acesso à informação, dados abertos e proteção de dados.",
        "Caso de política pública: interpretar indicadores de eficiência, eficácia e efetividade e propor medidas.",
        "Caso fiscal: comparar resultados primário e nominal e propor medidas de responsabilidade fiscal.",
    ]
    for day_index in range((exam - first).days):
        d = first + timedelta(days=day_index)
        ds = d.isoformat()
        daily = dict(
            date=ds,
            phase="Cobertura do edital" if d <= last_new else "Consolidação e reta final",
            lessons=[],
            activities=[],
        )
        if ds in sim:
            which = sim[ds]
            title = (
                "Simulado P1: 80 questões em até 4h"
                if which == "P1"
                else "Simulado P2 + P3: 40 questões A01 e 1 estudo de caso em até 4h"
            )
            daily["phase"] = "Simulado em dois dias"
            daily["activities"] = [
                dict(
                    id=f"sim-{ds}",
                    kind="simulation",
                    title=title,
                    minutes=240,
                    detail="Use provas da biblioteca ou seleção explícita do catálogo. Sem consulta. "
                    + (
                        "Calcule P1 com os pesos 1 e 2."
                        if which == "P1"
                        else "Reserve tempo para a discursiva de até 30 linhas. P2: 3 pontos por acerto. P3: autoavaliação qualitativa; sem nota oficial."
                    ),
                )
            ]
        else:
            if d <= last_new:
                idx = teaching.index(d)
                target = (len(ordered) * (idx + 1)) // len(teaching)
                selected = ordered[consumed:target]
                consumed = target
                daily["lessons"] = [u["lesson_id"] for u in selected]
                for u in selected:
                    u["scheduled_date"] = ds
            else:
                selected = []
            daily["activities"].append(
                dict(
                    id=f"review-{ds}",
                    kind="review",
                    title="Revisão de recuperação e caderno de erros",
                    minutes=30 if d <= last_new else 60,
                    detail="Recupere sem consulta as aulas previstas para D+1, D+7 e D+21; confira depois. Priorize erros e dúvidas. Se acumular, use parte do bloco de prática. Cartões seguem o agendamento individual do sistema.",
                )
            )
            remaining = 240 - sum(u["minutes"] for u in selected) - sum(a["minutes"] for a in daily["activities"])
            essay_day = d.weekday() in [1, 4] or d > last_new and d.weekday() != 5
            if essay_day:
                minutes = min(45, remaining)
                daily["activities"].append(
                    dict(
                        id=f"essay-{ds}",
                        kind="essay",
                        title="Treino P3: estudo de caso interdisciplinar",
                        minutes=minutes,
                        detail=cases[(day_index // 3) % len(cases)]
                        + " Escreva até 30 linhas: diagnóstico, fundamento, solução e controle. Revise aderência ao comando, precisão técnica, coerência e português. Exercício autoral, sem espelho oficial.",
                    )
                )
                remaining -= minutes
            if remaining:
                focus = (
                    "Corrigir simulados, fechar lacunas de A01, AFO, contabilidade, direito financeiro e fluência de dados."
                    if d > last_new
                    else "Selecionar questões do assunto estudado; priorizar FCC quando houver cobertura. Resolver sem ajuda, corrigir e explicar cada erro."
                )
                if ds == "2026-12-19":
                    focus = "Revisão leve de fórmulas, resumos e erros recorrentes. Conferir documento, trajeto, horários e materiais permitidos na convocação."
                daily["activities"].append(
                    dict(
                        id=f"practice-{ds}",
                        kind="practice",
                        title="Questões, correção e recuperação de atrasos"
                        if d <= last_new
                        else "Revisão dirigida e correção de simulados",
                        minutes=remaining,
                        detail=focus
                        + " Meta sugerida: 10 a 20 questões por hora, ajustando a dificuldade; não sacrificar a correção.",
                    )
                )
        assert (
            sum(next(u["minutes"] for u in ordered if u["lesson_id"] == lid) for lid in daily["lessons"])
            + sum(a["minutes"] for a in daily["activities"])
            == 240
        )
        days.append(daily)
    assert consumed == len(ordered)
    for daily in days:
        d = date.fromisoformat(daily["date"])
        daily["review_lesson_ids"] = [
            u["lesson_id"] for u in ordered if (d - date.fromisoformat(u["scheduled_date"])).days in (1, 7, 21)
        ]
    result = dict(
        id="apofp-sp-2026-a01",
        version=1,
        title="APOFP SP 2026 · A01",
        area="Orçamento e Finanças Públicas",
        board="FCC",
        start_date=first.isoformat(),
        exam_date=exam.isoformat(),
        coverage_deadline=last_new.isoformat(),
        daily_minutes=240,
        sources_checked="2026-10-29",
        source_url=PDF_URL,
        sources=[
            dict(title="Edital 01/2026 · abertura e Anexo II", url=PDF_URL, file="edital-01-2026.pdf"),
            dict(
                title="Edital 02/2026 · prova em 20/12/2026",
                url=BASE_URL + "Paginas/Editais-Apofp.aspx",
                file="retificacao-02-2026.pdf",
            ),
            dict(
                title="Edital 03/2026 · atendimento e perícia; programa mantido",
                url=BASE_URL + "Paginas/Editais-Apofp.aspx",
                file="retificacao-03-2026.pdf",
            ),
        ],
        scoring=dict(
            p1_max=112,
            p2_max=120,
            p3_max=120,
            p1_min=45,
            p2_min=48,
            p3_min=48,
            objective_min=116,
            p1_questions=80,
            p2_questions=40,
            p3_lines=30,
        ),
        strategy="Primeira passagem por todo o programa até 10/12, com sessões sugeridas de 63 minutos, recuperação diária, prática e duas rodadas de simulado. A conclusão registra a sessão; domínio depende de desempenho e revisão. Ajuste o bloco de prática para aprofundar aulas densas.",
        milestones=[
            dict(date="2026-11-03", title="Conferir inscrição, pagamento e solicitações na FCC"),
            dict(date="2026-11-13", title="Consultar deferimento da inscrição e atendimentos"),
            dict(date="2026-11-25", title="Consultar divulgação definitiva das inscrições"),
            dict(date="2026-12-08", title="Consultar convocação, local e horários das provas"),
            dict(date="2026-12-10", title="Meta: primeira passagem por todo o conteúdo A01 + P1/P3"),
            dict(date="2026-12-20", title="Provas P1 (manhã), P2 e P3 (tarde)"),
            dict(date="2027-01-04", title="Consultar questões e gabaritos a partir das 17h"),
            dict(date="2027-01-05", title="Início do prazo de recursos de gabarito: 05 e 06/01"),
            dict(date="2027-01-06", title="Início do envio de títulos: 06 a 08/01"),
        ],
        subjects=subjects,
        days=days,
        coverage=dict(
            subjects=len(subjects),
            lessons=len(lessons),
            source_sha256=hashlib.sha256((ROOT / "fontes" / "edital-01-2026.pdf").read_bytes()).hexdigest(),
            method="Partição contígua de todo o texto das 10 disciplinas básicas e da especialidade A01; remontagem validada por disciplina. B02/C03 excluídas por opção do candidato.",
        ),
    )
    (ROOT / "roadmap.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# APOFP SP 2026 — A01 · Orçamento e Finanças Públicas",
        "",
        "Plano de 29/10 a 19/12/2026, 4 horas diárias (208 horas). Prova prevista para 20/12/2026.",
        "",
        "Meta de primeira passagem: 10/12/2026. 94 aulas, 10 disciplinas básicas e a especialidade A01. Agrupamentos e datas são sugestões de estudo.",
        "",
        "## Método",
        "",
        result["strategy"],
        "",
        "Cada sessão sugerida tem 63 minutos: recuperar (10), pré-teste (5), estudar (20), reconstruir no quadro (10), questões (15), fechar (3). Aulas densas exigem aprofundamento no bloco de prática.",
        "",
        "Revisões D+1/D+7/D+21 usam a data planejada da aula. Se a sessão ocorrer depois, ajuste a recuperação pela data real. Cartões mantêm seu próprio agendamento do sistema.",
        "",
        "Prioridade: A01 (P2, peso 3), disciplinas de peso 2 em P1 e estudo de caso (P3). Preservar todas as matérias de peso 1. Questões são selecionadas explicitamente no catálogo; simulados são metas de prática com itens da biblioteca, sem caderno ou espelho oficial gerado.",
        "",
        "P1: 80 questões, 112 pontos, 4h pela manhã. P2: 40 questões, 120 pontos. P3: um caso sobre conhecimentos básicos, até 30 linhas e 120 pontos. P2 e P3 compartilham 4h à tarde. Mínimos cumulativos: 45 em P1, 48 em P2, 48 em P3 e 116 na soma de P1 e P2. A discursiva depende também da classificação para correção.",
        "",
        "## Cobertura do edital",
        "",
        "| Disciplina | Prova | Questões | Peso | Aulas |",
        "|---|---|---:|---:|---:|",
    ]
    lines += [
        f"| {s['name']} | {s['exam']} | {s['questions']} | {s['weight']} | {len(s['lessons'])} |" for s in subjects
    ]
    lines += [
        "",
        "O texto integral de cada disciplina foi particionado em trechos contíguos e reconstituído para conferir a cobertura. Cada aula conserva seu trecho, checklist e link para o Anexo II. B02 e C03 não integram a preparação da opção A01.",
        "",
        "## Marcos",
        "",
    ]
    lines += [f"- {m['date']}: {m['title']}." for m in result["milestones"]]
    lines += ["", "## Calendário diário", ""]
    by_id = {u["lesson_id"]: u for u in ordered}
    by_subject = {s["subject_id"]: s["name"] for s in subjects}
    for d in days:
        lines += [f"### {d['date']} · {d['phase']} · 4h", ""]
        lines += [
            f"- Aula ({by_id[lid]['minutes']} min): {by_subject[by_id[lid]['subject_id']]} — {by_id[lid]['title']}."
            for lid in d["lessons"]
        ]
        lines += [f"- {a['title']} ({a['minutes']} min): {a['detail']}" for a in d["activities"]]
        if d["review_lesson_ids"]:
            lines += [
                "- Recuperação prevista: " + "; ".join(by_id[lid]["title"] for lid in d["review_lesson_ids"]) + "."
            ]
        lines += [""]
    lines += [
        "## Fontes e manutenção",
        "",
        f"[Edital oficial e Anexo II]({PDF_URL}).",
        "",
        f"[Retificações 02/2026 e 03/2026]({BASE_URL}Paginas/Editais-Apofp.aspx). Conferidas em 29/10/2026. O edital 02 remarcou as provas; o 03 trata de atendimento/perícia e conserva o programa.",
        "",
        "Fontes originais em `fontes/`. Dados estruturados em `roadmap.json`. Regenerar com o Python do runtime: `scripts/build-apofp-roadmap.py` (requer pypdf).",
        "",
        "O importador `roadmap.py --install dados/estudo.sqlite` cria backup SQLite e adiciona o plano sem duplicar aulas ou apagar progresso. A interface acompanha aulas pelas sessões concluídas e permite marcar separadamente revisões, prática e simulados.",
    ]
    (ROOT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"subjects": len(subjects), "lessons": len(lessons), "days": len(days), "hours": len(days) * 4},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    build()
