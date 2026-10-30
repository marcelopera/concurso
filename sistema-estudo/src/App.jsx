import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Excalidraw } from "@excalidraw/excalidraw";
import { api, profileHeaders, selectProfile } from "./api";
import ProfileBox, { ResetRoadmap } from "./ProfileBox";
import RoadmapPlan, { SyllabusDetails } from "./RoadmapPlan";
import { LinkedQuestionList, MappingEvidence, MappingOverview } from "./QuestionLinks";

const STEPS = [
  { title: "Recuperar", minutes: 10, hint: "Escreva o que lembra. Sem consultar." },
  { title: "Pré-teste", minutes: 5, hint: "Pode chutar. Só o gabarito aparece." },
  { title: "Aula", minutes: 20, hint: "Estude no material. Anote só o que vale guardar." },
  { title: "Whiteboard", minutes: 10, hint: "Reconstrua as relações de memória." },
  { title: "Questões", minutes: 15, hint: "Comece com apoio. Termine sem." },
  { title: "Fechar", minutes: 3, hint: "Confirme o que vale guardar." },
];
const TRANSIENT_APP_STATE = new Set([
  "collaborators", "activeTool", "editingElement", "editingGroupId", "selectedElementIds",
  "openMenu", "openPopup", "openSidebar", "width", "height", "offsetTop", "offsetLeft",
]);

function serializableAppState(appState) {
  const result = {};
  for (const [key, value] of Object.entries(appState || {})) {
    if (TRANSIENT_APP_STATE.has(key)) continue;
    try { JSON.stringify(value); result[key] = value; } catch { /* estado transitório do editor */ }
  }
  return result;
}

function errorText(error) {
  return error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
}

function Notice({ children, kind = "info", onClose }) {
  if (!children) return null;
  return <div className={"notice " + kind} role="status">
    <span>{children}</span>{onClose && <button className="icon-button" onClick={onClose} aria-label="Fechar aviso">×</button>}
  </div>;
}

function Button({ children, secondary = false, small = false, disabled = false, ...props }) {
  return <button className={"button" + (secondary ? " secondary" : "") + (small ? " small" : "")} disabled={disabled} {...props}>{children}</button>;
}

function Chip({ children, active = false, ...props }) {
  return <button className={"chip" + (active ? " active" : "")} {...props}>{children}</button>;
}

function StatusTag({ question }) {
  const status = question.reference_status || {};
  if (status.correctable) return <span className="tag good">Gabarito definitivo · corrigível</span>;
  let text = "Consulta sem avaliação automática";
  if (status.state === "divergente") text = "Gabaritos divergentes · consulta";
  else if (status.situation === "anulado") text = "Item anulado · consulta";
  else if (status.state === "concordante" && status.situation === "valido" && !status.has_definitive) text = "Sem definitivo identificado · consulta";
  else if (status.extraction && status.extraction !== "extraido") text = "Extração pendente · consulta";
  else if (status.situation === "valido") text = "Gabarito sem definitivo · consulta";
  return <span className="tag">{text}</span>;
}

function QuestionResult({ result, pretest = false }) {
  if (!result) return null;
  const snapshot = result.snapshot || {};
  const answered = result.question || {};
  const label = (x) => x == null || x === "" ? "sem resposta publicada" : String(x);
  if (pretest) {
    return <div className="feedback">
      {snapshot.auto_graded
        ? <><strong>Gabarito: {label(snapshot.reference_answer)}.</strong><span>Resposta registrada.</span></>
        : <><strong>Resposta registrada sem correção automática.</strong><span>Consulte as fontes associadas depois do pré-teste.</span></>}
    </div>;
  }
  return <div className="feedback">
    {result.correct === null
      ? <strong>Resposta registrada · sem avaliação automática</strong>
      : <strong>{result.correct ? "Acertou" : "Errou"} · gabarito {label(snapshot.reference_answer)}</strong>}
    {!snapshot.auto_graded && <span>Estado da referência: {snapshot.state || "sem referência consolidada"}{snapshot.situation ? " · " + snapshot.situation : ""}. A base não fornece explicação comentada.</span>}
    {Array.isArray(snapshot.associated_answers) && snapshot.associated_answers.length > 0 && <div className="source-list">
      <span className="muted">Fontes associadas ao gabarito</span>
      {snapshot.associated_answers.map((source, index) => <div className="source-row" key={source.document_id + "-" + index}>
        <span>{source.document_title || "Documento de gabarito"} · {label(source.answer)} · {source.nature || "tipo não indicado"}{source.situation ? " · " + source.situation : ""}{source.pages?.length ? " · página" + (source.pages.length > 1 ? "s " : " ") + source.pages.join(", ") : ""}</span>
        {source.document_id && <a href={"/api/library/file?document_id=" + encodeURIComponent(source.document_id) + (source.pages?.[0] ? "#page=" + source.pages[0] : "")} target="_blank" rel="noreferrer">Abrir PDF</a>}
      </div>)}
    </div>}
    {answered.reference_status && !snapshot.associated_answers?.length && <span>Sem documento de gabarito associado a esta ocorrência.</span>}
  </div>;
}

function QuestionCard({ question, onSubmit, result, helpUsed, onHelpChange, variant = "normal", pending = false }) {
  const [essay, setEssay] = useState("");
  if (!question) return null;
  const answerLocked = Boolean(result) || pending;
  const metadata = [question.bank, question.contest, question.number ? "Questão " + question.number : null, question.discipline].filter(Boolean).join(" · ");
  return <div className="card question-card">
    <div className="tag-row"><StatusTag question={question} />{question.format && <span className="tag">{question.format === "certo_errado" ? "Certo ou errado" : question.format === "multipla_escolha" ? "Múltipla escolha" : question.format}</span>}</div>
    <MappingEvidence mapping={question.mapping} />
    <p className="muted question-meta">{metadata}</p>
    {question.contexts?.map((context, index) => <details className="context" key={index}><summary>Texto-base {question.contexts.length > 1 ? index + 1 : ""}</summary><p>{context}</p></details>)}
    {question.source_document_id && <a className="question-source" href={"/api/library/file?document_id=" + encodeURIComponent(question.source_document_id) + (question.pages?.[0] ? "#page=" + question.pages[0] : "")} target="_blank" rel="noreferrer">Fonte original · PDF{question.pages?.length ? " · página" + (question.pages.length > 1 ? "s " : " ") + question.pages.join(", ") : ""}</a>}
    <p className="question-stem">{question.stem}</p>
    {question.alternatives?.length ? <div className="options">
      {question.alternatives.map((choice) => <button className="option" disabled={answerLocked} key={choice.label} onClick={() => onSubmit(choice.label)}>
        <b>{choice.label}</b><span>{choice.text}</span>
      </button>)}
    </div> : <div className="essay-answer">
      <textarea value={essay} onChange={(e) => setEssay(e.target.value)} disabled={answerLocked} placeholder="Registre sua resposta" aria-label="Resposta discursiva" />
      <Button disabled={answerLocked || !essay.trim()} onClick={() => onSubmit(essay.trim())}>{pending ? "Salvando…" : "Enviar resposta"}</Button>
    </div>}
    {variant !== "pretest" && onHelpChange && <div className="question-tools">
      <Chip active={helpUsed} onClick={() => onHelpChange(!helpUsed)}>Usei ajuda</Chip>
      {question.pages?.length > 0 && <span className="muted">Página{question.pages.length > 1 ? "s" : ""}: {question.pages.join(", ")}</span>}
    </div>}
    <QuestionResult result={result} pretest={variant === "pretest"} />
  </div>;
}

function CatalogBrowser({ mode, selectedIds = [], onToggle, onChoose, initialEligible = true }) {
  const [search, setSearch] = useState("");
  const [bank, setBank] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [eligibleOnly, setEligibleOnly] = useState(initialEligible);
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], banks: [], disciplines: [], pages: 1, total: 0 });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let live = true;
    const timeout = setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ search, bank, discipline, page: String(page), eligible_only: eligibleOnly ? "1" : "0" });
        const result = await api("/api/catalog?" + params.toString());
        if (live) { setData(result); setError(""); }
      } catch (e) { if (live) setError(errorText(e)); }
      finally { if (live) setLoading(false); }
    }, search ? 260 : 0);
    return () => { live = false; clearTimeout(timeout); };
  }, [search, bank, discipline, page, eligibleOnly]);
  return <section className="catalog">
    <div className="catalog-filters">
      <label className="field grow"><span>Buscar no enunciado, banca ou prova</span><input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Ex.: orçamento, FCC, 2024…" /></label>
      <label className="field"><span>Banca</span><select value={bank} onChange={(e) => { setBank(e.target.value); setPage(1); }}><option value="">Todas</option>{data.banks.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label className="field"><span>Disciplina</span><select value={discipline} onChange={(e) => { setDiscipline(e.target.value); setPage(1); }}><option value="">Todas</option>{data.disciplines.map((item) => <option key={item}>{item}</option>)}</select></label>
    </div>
    <label className="check-line"><input type="checkbox" checked={eligibleOnly} onChange={(e) => { setEligibleOnly(e.target.checked); setPage(1); }} />Mostrar só questões com gabarito definitivo corrigível</label>
    <p className="muted catalog-count">{loading ? "Buscando…" : data.total.toLocaleString("pt-BR") + " ocorrências"}{!eligibleOnly && " · itens fora do critério aparecem para consulta, sem correção automática"}</p>
    {error && <Notice kind="error">{error}</Notice>}
    {eligibleOnly && data.total === 0 && !loading && <div className="empty compact"><strong>Nenhum item corrigível para este filtro.</strong><span>Desmarque o filtro para consultar os itens disponíveis com aviso de status.</span></div>}
    {!eligibleOnly && data.total === 0 && !loading && <div className="empty compact"><strong>Nenhuma ocorrência encontrada.</strong><span>Altere os filtros ou tente outra busca.</span></div>}
    <div className="catalog-list">
      {data.items.map((question) => {
        const selected = selectedIds.includes(question.occurrence_id);
        return <article className="catalog-item" key={question.occurrence_id}>
          <div className="catalog-item-copy">
            <div className="tag-row"><StatusTag question={question} /><span className="tag">{question.bank}</span></div>
            <strong>{question.discipline || question.block || "Disciplina não identificada"} · {question.contest}{question.number ? " · nº " + question.number : ""}</strong>
            <p>{question.stem}</p>
            {question.contexts?.length > 0 && <span className="muted">Inclui texto-base</span>}
          </div>
          {mode === "select"
            ? <Button small secondary={selected} onClick={() => onToggle(question)}>{selected ? "Selecionada ✓" : "Vincular"}</Button>
            : <Button small onClick={() => onChoose(question)}>Responder</Button>}
        </article>;
      })}
    </div>
    {data.pages > 1 && <div className="pagination"><Button small secondary disabled={page <= 1} onClick={() => setPage((x) => Math.max(1, x - 1))}>Anterior</Button><span className="muted">Página {page} de {data.pages}</span><Button small secondary disabled={page >= data.pages} onClick={() => setPage((x) => Math.min(data.pages, x + 1))}>Próxima</Button></div>}
  </section>;
}

function Roadmap({ data, onOpenTopic, onResume, onCreateTopic, onOpenLesson, onStart, onRefresh }) {
  const [adding, setAdding] = useState(data.subjects.length === 0);
  const [subject, setSubject] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [view, setView] = useState(data.roadmap ? "daily" : "syllabus");
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState("all");
  const plan = data.roadmap;
  const total = plan?.stats.lessons ?? data.totals?.lessons ?? 0;
  const completed = plan?.stats.completed ?? data.totals?.completed ?? 0;
  const visibleSubjects = data.subjects.filter((s) => {
    const info = plan?.subject_info.find((x) => x.name === s.name);
    return (scope !== "P1" || info?.exam === "P1") && (scope !== "P2" || info?.exam === "P2") &&
      (!search.trim() || [s.name, ...s.topics.flatMap((t) => [t.title, ...t.lessons.map((l) => l.title)])].join(" ").toLocaleLowerCase("pt-BR").includes(search.toLocaleLowerCase("pt-BR")));
  });
  const percent = total ? Math.round(completed / total * 100) : 0;
  async function submit(e) {
    e.preventDefault();
    setSaving(true); setError("");
    try { await onCreateTopic(subject, title); setAdding(false); setSubject(""); setTitle(""); }
    catch (err) { setError(errorText(err)); }
    finally { setSaving(false); }
  }
  return <>
    <div className="page-heading"><div><h1>Roadmap{plan ? " · APOFP SP" : ""}</h1><p className="muted">{plan ? "A01 · Orçamento e Finanças Públicas · 4 horas por dia" : "Aulas criadas por você e progresso registrado."}</p></div><Button secondary small onClick={() => setAdding((x) => !x)}>{adding ? "Fechar" : "+ Novo tópico"}</Button></div>
    {data.active_session && <div className="resume-card"><div><span className="tag">Sessão em andamento</span><strong>{data.active_session.subject_name} · {data.active_session.topic_title}</strong><span>{data.active_session.lesson_title} · etapa {data.active_session.current_step + 1} de 6</span></div><Button onClick={onResume}>Retomar sessão</Button></div>}
    <div className="progress-overview"><div><span className="muted">Progresso do roadmap</span><strong>{completed} de {total} aulas concluídas</strong></div><span className="progress-pct">{percent}%</span><div className="progress-track"><span style={{ width: percent + "%" }} /></div></div>
    {plan && <ResetRoadmap profile={data.profile} onRefresh={onRefresh} />}
    {plan && <div className="plan-tabs" role="group" aria-label="Visualização do roadmap"><Chip active={view === "daily"} onClick={() => setView("daily")}>Plano diário</Chip><Chip active={view === "syllabus"} onClick={() => setView("syllabus")}>Conteúdo do edital</Chip></div>}
    {plan?.question_mapping && <MappingOverview mapping={plan.question_mapping} onOpenLesson={onOpenLesson} />}
    {plan && view === "daily" && <RoadmapPlan plan={plan} onOpenLesson={onOpenLesson} onStart={onStart} onRefresh={onRefresh} />}
    {adding && <form className="card create-topic" onSubmit={submit}>
      <h2>Novo tópico</h2><p className="muted">Comece pelo que quer estudar. As questões são vinculadas manualmente depois.</p>
      <div className="form-grid"><label className="field"><span>Disciplina</span><input required value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Ex.: Direito Administrativo" /></label><label className="field"><span>Tópico</span><input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex.: Atos administrativos" /></label></div>
      {error && <Notice kind="error">{error}</Notice>}<div className="actions"><Button disabled={saving}>{saving ? "Salvando…" : "Criar tópico"}</Button></div>
    </form>}
    {data.subjects.length === 0 && !adding && <div className="empty"><strong>Seu roadmap começa aqui.</strong><span>Crie uma disciplina e um tópico para organizar as aulas.</span></div>}
    {view === "syllabus" && <div className="form-grid syllabus-filter"><label className="field grow"><span>Buscar no conteúdo</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Disciplina, tópico ou aula" /></label>{plan && <label className="field" htmlFor="roadmap-exam"><span>Prova</span><select id="roadmap-exam" aria-label="Prova" value={scope} onChange={(e) => setScope(e.target.value)}><option value="all">Todas</option><option value="P1">P1 / P3 · Comum</option><option value="P2">P2 · Específico A01</option></select></label>}</div>}
    {view === "syllabus" && visibleSubjects.length === 0 && <p className="muted">Nenhum conteúdo encontrado.</p>}
    {view === "syllabus" && visibleSubjects.map((subjectItem) => <section className="subject-section" key={subjectItem.id}>
      <div className="section-title"><h2>{subjectItem.name}</h2><span className="muted">{plan?.subject_info.find((x) => x.name === subjectItem.name) && <>{plan.subject_info.find((x) => x.name === subjectItem.name).exam} · peso {plan.subject_info.find((x) => x.name === subjectItem.name).weight} · </>}{subjectItem.topics.reduce((sum, item) => sum + item.lessons.filter((lesson) => lesson.completed_at).length, 0)} aulas concluídas</span></div>
      {subjectItem.topics.map((topic) => {
        const topicDone = topic.lessons.filter((lesson) => lesson.completed_at).length;
        const topicTotal = topic.lessons.length;
        const topicPercent = topicTotal ? Math.round(topicDone / topicTotal * 100) : 0;
        return <button className="topic-row" key={topic.id} onClick={() => onOpenTopic(subjectItem, topic)}>
          <span className="topic-row-main"><strong>{topic.title}</strong><span>{topicTotal === 0 ? "Sem aulas · comece adicionando uma" : topicDone + " de " + topicTotal + " aulas"}</span></span>
          <span className="topic-progress"><span className="mini-track"><i style={{ width: topicPercent + "%" }} /></span><span className="arrow">›</span></span>
        </button>;
      })}
    </section>)}
  </>;
}

function TopicPage({ subject, topic, onBack, onOpenLesson, onCreateLesson, onRefresh }) {
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError("");
    try { const lesson = await onCreateLesson(topic.id, title); setTitle(""); await onRefresh(); onOpenLesson(lesson.id); }
    catch (err) { setError(errorText(err)); }
    finally { setBusy(false); }
  }
  return <>
    <button className="back-link" onClick={onBack}>‹ Roadmap</button>
    <div className="page-heading"><div><p className="muted eyebrow">{subject.name}</p><h1>{topic.title}</h1><p className="muted">Organize aulas e escolha as questões que fazem parte delas.</p></div></div>
    <form className="card create-lesson" onSubmit={submit}>
      <h2>Adicionar aula</h2><div className="form-grid"><label className="field grow"><span>Título da aula</span><input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex.: Conceito e atributos" /></label><Button disabled={busy}>{busy ? "Criando…" : "Adicionar aula"}</Button></div>{error && <Notice kind="error">{error}</Notice>}
    </form>
    <div className="section-title"><h2>Aulas</h2><span className="muted">{topic.lessons.length} no tópico</span></div>
    {topic.lessons.length === 0 ? <div className="empty"><strong>Este tópico ainda não tem aulas.</strong><span>Crie a primeira aula para adicionar materiais e questões.</span></div> : <div className="lesson-list">
      {topic.lessons.map((lesson) => <article className="lesson-row card" key={lesson.id}>
        <div><strong>{lesson.title}</strong><span className="muted">{lesson.completed_at ? "Concluída" : "Nova aula"} · {lesson.question_count || 0} questões vinculadas</span></div>
        <Button secondary small onClick={() => onOpenLesson(lesson.id)}>Configurar</Button>
      </article>)}
    </div>}
  </>;
}

function ExcalScene({ scene, onChange, readOnly = false, theme = "light", label = "Quadro" }) {
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const apiRef = useRef(null);
  const latestElementsRef = useRef([]);
  const sceneReadyRef = useRef(false);
  const didFitRef = useRef(false);
  const initialData = useMemo(() => ({
    elements: scene?.elements || [],
    appState: { viewBackgroundColor: "#ffffff", ...serializableAppState(scene?.appState), theme },
    files: scene?.files || {},
  }), []);
  const fitReadOnlyScene = useCallback(() => {
    if (!readOnly || didFitRef.current || !sceneReadyRef.current || !apiRef.current) return;
    didFitRef.current = true;
    const api = apiRef.current;
    const elements = latestElementsRef.current;
    requestAnimationFrame(() => api.scrollToContent(elements, {
      fitToViewport: true,
      viewportZoomFactor: 0.85,
      maxZoom: 1,
      canvasOffsets: { top: 12, right: 12, bottom: 64, left: 12 },
      animate: false,
    }));
  }, [readOnly]);
  const receiveExcalidrawAPI = useCallback((api) => {
    apiRef.current = api;
    fitReadOnlyScene();
  }, [fitReadOnlyScene]);
  const changed = useCallback((elements, appState, files) => {
    latestElementsRef.current = elements || [];
    if (latestElementsRef.current.length > 0) {
      sceneReadyRef.current = true;
      fitReadOnlyScene();
    }
    if (onChangeRef.current) onChangeRef.current({ elements, appState: serializableAppState(appState), files: files || {} });
  }, [fitReadOnlyScene]);
  return <div className={"excal-container" + (readOnly ? " read-only" : "")} aria-label={label}>
    <Excalidraw initialData={initialData} onChange={changed} excalidrawAPI={readOnly ? receiveExcalidrawAPI : undefined} viewModeEnabled={readOnly} theme={theme} langCode="pt-BR" />
  </div>;
}

function SceneEditor({ scene, theme, onSave, onClose }) {
  const [draft, setDraft] = useState(scene || { elements: [], appState: {}, files: {} });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  return <div className="modal-backdrop" role="presentation">
    <section className="modal scene-modal" role="dialog" aria-modal="true" aria-label="Editar quadro de referência">
      <div className="modal-heading"><div><h2>Quadro de referência</h2><p className="muted">A cena fica vinculada a esta aula e aparece ao comparar durante o estudo.</p></div><button className="icon-button" aria-label="Fechar" onClick={onClose}>×</button></div>
      <ExcalScene scene={draft} theme={theme} onChange={setDraft} label="Editor do quadro de referência" />
      {error && <Notice kind="error">{error}</Notice>}
      <div className="actions"><Button secondary onClick={onClose}>Cancelar</Button><Button disabled={saving} onClick={async () => { setSaving(true); setError(""); try { await onSave(draft); onClose(); } catch (e) { setError(errorText(e)); } finally { setSaving(false); } }}>{saving ? "Salvando…" : "Salvar referência"}</Button></div>
    </section>
  </div>;
}

function LibraryPicker({ onChoose, onClose }) {
  const [search, setSearch] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let live = true;
    const timeout = setTimeout(async () => {
      setLoading(true);
      try { const result = await api("/api/library?search=" + encodeURIComponent(search)); if (live) { setItems(result.items || []); setError(""); } }
      catch (e) { if (live) setError(errorText(e)); }
      finally { if (live) setLoading(false); }
    }, search ? 250 : 0);
    return () => { live = false; clearTimeout(timeout); };
  }, [search]);
  return <div className="modal-backdrop" role="presentation">
    <section className="modal library-modal" role="dialog" aria-modal="true" aria-label="Escolher PDF da biblioteca">
      <div className="modal-heading"><div><h2>PDF da biblioteca</h2><p className="muted">Arquivos disponíveis localmente na biblioteca de concursos.</p></div><button className="icon-button" aria-label="Fechar" onClick={onClose}>×</button></div>
      <label className="field"><span>Buscar por prova, banca ou arquivo</span><input autoFocus value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Ex.: 2024 MPO definitivo" /></label>
      {error && <Notice kind="error">{error}</Notice>}{loading && <p className="muted">Buscando PDFs…</p>}
      <div className="library-list">{items.map((item) => <button className="library-item" key={item.documento_id} onClick={() => onChoose(item)}>
        <span className="pdf-icon">PDF</span><span><strong>{item.nome || item.titulo || item.concurso}</strong><small>{[item.concurso,item.banca,item.tipo].filter(Boolean).join(" · ")}</small></span><span className="arrow">›</span>
      </button>)}</div>
      {!loading && !items.length && <div className="empty compact"><strong>Nenhum PDF encontrado.</strong><span>A busca considera arquivos existentes dentro da biblioteca.</span></div>}
    </section>
  </div>;
}

function LessonEditor({ lessonId, onBack, onStart, onRefresh, theme }) {
  const [lesson, setLesson] = useState(null);
  const [title, setTitle] = useState("");
  const [selected, setSelected] = useState([]);
  const [picker, setPicker] = useState(false);
  const [library, setLibrary] = useState(false);
  const [referenceEditor, setReferenceEditor] = useState(false);
  const [materialTitle, setMaterialTitle] = useState("");
  const [url, setUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function reload() {
    const result = await api("/api/lessons/" + lessonId);
    setLesson(result); setTitle(result.title); setSelected(result.occurrence_ids || []);
  }
  useEffect(() => { reload().catch((e) => setError(errorText(e))); }, [lessonId]);
  async function saveTitle() {
    setSaving(true); setError("");
    try { const result = await api("/api/lessons/" + lessonId, { method: "PUT", body: { title } }); setLesson(result); setTitle(result.title); }
    catch (e) { setError(errorText(e)); }
    finally { setSaving(false); }
  }
  async function saveQuestions() {
    setSaving(true); setError("");
    try { const result = await api("/api/lessons/" + lessonId + "/questions", { method: "PUT", body: { occurrence_ids: selected } }); setLesson(result); setSelected(result.occurrence_ids || []); return true; }
    catch (e) { setError(errorText(e)); return false; }
    finally { setSaving(false); }
  }
  async function addMaterial(data) {
    setSaving(true); setError("");
    try { const result = await api("/api/lessons/" + lessonId + "/materials", { method: "POST", body: data }); setLesson(result); setMaterialTitle(""); setUrl(""); setLibrary(false); }
    catch (e) { setError(errorText(e)); }
    finally { setSaving(false); }
  }
  async function removeMaterial(id) {
    setError("");
    try { await api("/api/materials/" + id, { method: "DELETE" }); await reload(); }
    catch (e) { setError(errorText(e)); }
  }
  async function saveReference(scene) {
    const result = await api("/api/lessons/" + lessonId, { method: "PUT", body: { title, reference_scene: scene } });
    setLesson(result);
  }
  if (!lesson) return <><button className="back-link" onClick={onBack}>‹ Tópico</button><div className="empty"><strong>Carregando aula…</strong>{error && <span>{error}</span>}</div></>;
  return <>
    <button className="back-link" onClick={onBack}>‹ {lesson.topic_title}</button>
    <div className="page-heading"><div><p className="muted eyebrow">{lesson.subject_name} · {lesson.topic_title}</p><h1>Configurar aula</h1></div><Button onClick={onStart}>Iniciar sessão</Button></div>
    <SyllabusDetails unit={lesson.roadmap} />
    {error && <Notice kind="error" onClose={() => setError("")}>{error}</Notice>}
    <section className="card editor-card"><div className="section-title"><h2>Identificação</h2><span className="muted">{lesson.completed_at ? "Aula concluída" : "Ainda não concluída"}</span></div>
      <div className="form-grid"><label className="field grow"><span>Título</span><input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={180} /></label><Button secondary disabled={saving || title.trim() === lesson.title} onClick={saveTitle}>{saving ? "Salvando…" : "Salvar título"}</Button></div>
    </section>
    <section className="card editor-card"><div className="section-title"><h2>Materiais</h2><span className="muted">{lesson.materials.length}</span></div>
      {lesson.materials.length ? <div className="material-list">{lesson.materials.map((material) => <div className="material-row" key={material.material_id}>
        <span className="material-symbol">{material.document_id ? "PDF" : "↗"}</span><div className="grow"><strong>{material.title}</strong><span className="muted">{material.document_id ? "PDF da biblioteca local" : material.url}</span></div>
        <a className="button secondary small" href={material.open_url} target="_blank" rel="noreferrer">Abrir</a><button className="icon-button" onClick={() => removeMaterial(material.material_id)} aria-label="Remover material">×</button>
      </div>)}</div> : <p className="muted">Adicione um link ou um PDF para usar durante a aula.</p>}
      <form className="material-add" onSubmit={(e) => { e.preventDefault(); addMaterial({ title: materialTitle || url, url }); }}>
        <label className="field grow"><span>Link HTTP ou HTTPS</span><input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" /></label><label className="field grow"><span>Nome para exibir</span><input value={materialTitle} onChange={(e) => setMaterialTitle(e.target.value)} placeholder="Nome do material" /></label><Button secondary disabled={!url.trim() || saving}>Adicionar link</Button>
      </form>
      <div className="row"><Button secondary onClick={() => setLibrary(true)}>Escolher PDF da biblioteca</Button></div>
    </section>
    <section className="card editor-card"><div className="section-title"><h2>Questões vinculadas</h2><span className="muted">{selected.length} selecionadas</span></div>
      <p className="muted">Confira o enunciado, a evidência da correspondência e o estado do gabarito. Você pode acrescentar ou remover vínculos e salvar a seleção. Itens correlatos ajudam nos fundamentos e podem exigir adaptação ao contexto da aula.</p>
      {lesson.questions.length ? <LinkedQuestionList questions={lesson.questions} selected={selected} onRemove={(id) => setSelected((ids) => ids.filter((item) => item !== id))} /> : <div className="empty compact"><strong>Nenhuma questão vinculada.</strong><span>O acervo ainda não tem correspondência confirmada para esta aula. Selecione itens do catálogo quando houver conteúdo pertinente.</span></div>}
      <div className="actions"><Button secondary onClick={() => setPicker(true)}>Selecionar do catálogo</Button><Button disabled={saving || JSON.stringify(selected) === JSON.stringify(lesson.occurrence_ids)} onClick={saveQuestions}>{saving ? "Salvando…" : "Salvar vínculos"}</Button></div>
    </section>
    <section className="card editor-card"><div className="section-title"><h2>Quadro de referência</h2><span className="muted">{lesson.reference_scene?.elements?.length ? "Cena salva" : "Opcional"}</span></div>
      <p className="muted">Desenhe a referência que poderá ser comparada visualmente ao quadro da sessão. Não há avaliação automática.</p>
      <div className="actions"><Button secondary onClick={() => setReferenceEditor(true)}>{lesson.reference_scene ? "Editar quadro" : "Criar quadro de referência"}</Button>{lesson.reference_scene && <Button secondary onClick={async () => { try { const result = await api("/api/lessons/" + lessonId, { method: "PUT", body: { title, reference_scene: null } }); setLesson(result); } catch (e) { setError(errorText(e)); } }}>Remover referência</Button>}</div>
    </section>
    <div className="actions bottom-actions"><Button secondary onClick={onBack}>Voltar ao tópico</Button><Button onClick={onStart}>Iniciar sessão</Button></div>
    {picker && <div className="modal-backdrop" role="presentation"><section className="modal picker-modal" role="dialog" aria-modal="true" aria-label="Selecionar questões">
      <div className="modal-heading"><div><h2>Selecionar questões</h2><p className="muted">Marque as ocorrências que pertencem a esta aula.</p></div><button className="icon-button" onClick={() => setPicker(false)} aria-label="Fechar">×</button></div>
      <CatalogBrowser mode="select" selectedIds={selected} onToggle={(item) => setSelected((ids) => ids.includes(item.occurrence_id) ? ids.filter((id) => id !== item.occurrence_id) : [...ids, item.occurrence_id])} />
      <div className="actions"><Button secondary onClick={() => setPicker(false)}>Cancelar</Button><Button disabled={saving} onClick={async () => { if (await saveQuestions()) setPicker(false); }}>Salvar seleção ({selected.length})</Button></div>
    </section></div>}
    {library && <LibraryPicker onClose={() => setLibrary(false)} onChoose={(item) => addMaterial({ title: item.nome || item.titulo || item.concurso || "PDF", document_id: item.documento_id })} />}
    {referenceEditor && <SceneEditor theme={theme} scene={lesson.reference_scene} onClose={() => setReferenceEditor(false)} onSave={saveReference} />}
  </>;
}

function ReviewCard({ card, onGrade }) {
  const [revealed, setRevealed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function grade(value) { setSaving(true); setError(""); try { await onGrade(card.card_id, value); } catch (e) { setError(errorText(e)); } finally { setSaving(false); } }
  return <div className="card review-card"><span className="tag">Revisão vencida · {card.subject_name} / {card.topic_title}</span><p className="question-stem">{card.front}</p>
    {revealed ? <><div className="answer-box">{card.back}</div><p className="muted">Intervalo atual: {card.interval_days} dia{card.interval_days > 1 ? "s" : ""}</p><div className="rating-row"><Button secondary disabled={saving} onClick={() => grade("errei")}>Errei · 1 dia</Button><Button secondary disabled={saving} onClick={() => grade("dificil")}>Difícil · manter</Button><Button disabled={saving} onClick={() => grade("facil")}>Fácil · avançar</Button></div></>
      : <Button onClick={() => setRevealed(true)}>Mostrar resposta</Button>}
    {error && <Notice kind="error">{error}</Notice>}
  </div>;
}

function StudySession({ initialSession, lesson, onExit, onDone, theme }) {
  const [session, setSession] = useState(initialSession);
  const [payload, setPayload] = useState(() => ({
    recallText: "", pretestOccurrenceId: lesson.questions?.[0]?.occurrence_id || "", notes: [], noteDraft: { text: "", origin: "", type: "cartão" },
    boardScene: { elements: [], appState: {}, files: {} }, questionIndex: 0, practiceResults: {}, helpByOccurrence: {}, pretestResult: null,
    closeCards: [], difficulties: [], reviewIds: [], ...(initialSession.payload || {}),
  }));
  const payloadRef = useRef(payload);
  const saveChain = useRef(Promise.resolve());
  const saveTimer = useRef(null);
  const saveVersion = useRef(0);
  const [saveStatus, setSaveStatus] = useState("saved");
  const [saveError, setSaveError] = useState("");
  const [remaining, setRemaining] = useState(initialSession.timer?.remaining_seconds ?? STEPS[initialSession.current_step].minutes * 60);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [dueCards, setDueCards] = useState([]);
  const [done, setDone] = useState(initialSession.status === "completed");
  const [difficultyDraft, setDifficultyDraft] = useState("");
  const [showReference, setShowReference] = useState(false);
  const step = session.current_step;
  const practiceQuestions = Array.isArray(payload.practiceOccurrenceIds)
    ? payload.practiceOccurrenceIds.map((id) => lesson.questions.find((q) => q.occurrence_id === id)).filter(Boolean)
    : lesson.questions;
  const currentQuestion = practiceQuestions?.[payload.questionIndex || 0];
  const pretestQuestion = lesson.questions?.find((q) => q.occurrence_id === payload.pretestOccurrenceId) || lesson.questions?.[0];
  const recallQuestion = payload.recallOccurrenceId ? lesson.questions.find((q) => q.occurrence_id === payload.recallOccurrenceId) : lesson.questions?.[1];
  const finishedReviews = new Set(payload.reviewIds || []);
  const nextReview = dueCards.find((card) => !finishedReviews.has(card.card_id));

  function sendSave(value) {
    const version = ++saveVersion.current;
    setSaveStatus("saving"); setSaveError("");
    const task = saveChain.current.catch(() => null).then(() => api("/api/sessions/" + session.session_id + "/state", { method: "PUT", body: { payload: value } }));
    saveChain.current = task;
    return task.then((saved) => { if (version === saveVersion.current) { setSession((current) => ({ ...current, ...saved })); setSaveStatus("saved"); } return saved; }, (error) => { if (version === saveVersion.current) { setSaveStatus("error"); setSaveError(errorText(error)); } throw error; });
  }
  function scheduleSave(value) {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => sendSave(value).catch(() => {}), 650);
  }
  function updatePayload(patch) {
    const previous = payloadRef.current;
    const next = typeof patch === "function" ? patch(previous) : { ...previous, ...patch };
    payloadRef.current = next; setPayload(next); setSaveStatus("saving"); setSaveError(""); scheduleSave(next);
    return next;
  }
  async function flush() {
    clearTimeout(saveTimer.current);
    return sendSave(payloadRef.current);
  }
  useEffect(() => {
    let live = true;
    api("/api/cards/due").then((result) => { if (live) setDueCards(result.items || []); }).catch((e) => { if (live) setActionError(errorText(e)); });
    return () => { live = false; clearTimeout(saveTimer.current); };
  }, []);
  useEffect(() => {
    function sendPendingSave() {
      const body = JSON.stringify({ payload: payloadRef.current });
      if (body.length > 60000) return false;
      fetch("/api/sessions/" + session.session_id + "/state", {
        method: "PUT", headers: { ...profileHeaders(), "Content-Type": "application/json" }, body, keepalive: true, credentials: "same-origin",
      }).catch(() => {});
      return true;
    }
    function beforeUnload(event) {
      if (!saveTimer.current && saveStatus === "saved") return;
      if (!sendPendingSave() || saveStatus === "error") { event.preventDefault(); event.returnValue = ""; }
    }
    function pageHide() {
      if (saveTimer.current || saveStatus !== "saved") sendPendingSave();
    }
    window.addEventListener("beforeunload", beforeUnload);
    window.addEventListener("pagehide", pageHide);
    return () => { window.removeEventListener("beforeunload", beforeUnload); window.removeEventListener("pagehide", pageHide); };
  }, [session.session_id, saveStatus]);
  useEffect(() => {
    const update = () => {
      const timer = session.timer || {};
      if (timer.paused) { setRemaining(timer.remaining_seconds || 0); return; }
      if (timer.deadline_at) setRemaining(Math.max(0, Math.ceil((Date.parse(timer.deadline_at) - Date.now()) / 1000)));
      else setRemaining(STEPS[step].minutes * 60);
    };
    update(); const handle = setInterval(update, 500);
    return () => clearInterval(handle);
  }, [session.timer, step]);

  async function navigate(nextStep) {
    setActionError(""); setBusy(true);
    try {
      if (nextStep === 5 && !payloadRef.current.closeCards?.length) {
        updatePayload((value) => ({ ...value, closeCards: (value.notes || []).map((note) => ({ id: note.id, selected: false, front: note.text, back: "", difficulty: "" })) }));
      }
      await flush();
      const result = await api("/api/sessions/" + session.session_id + "/step", { method: "POST", body: { step: nextStep } });
      setSession((current) => ({ ...current, ...result })); setRemaining(result.timer.remaining_seconds); window.scrollTo(0, 0);
    } catch (e) { setActionError(errorText(e)); }
    finally { setBusy(false); }
  }
  async function togglePause() {
    setActionError(""); setBusy(true);
    try { await flush(); const result = await api("/api/sessions/" + session.session_id + "/pause", { method: "POST", body: {} }); setSession((current) => ({ ...current, ...result })); setRemaining(result.timer.remaining_seconds); }
    catch (e) { setActionError(errorText(e)); }
    finally { setBusy(false); }
  }
  async function submitAnswer(stage, question, answer, help = false) {
    setActionError(""); setBusy(true);
    try {
      const result = await api("/api/sessions/" + session.session_id + "/answer", { method: "POST", body: { stage, occurrence_id: question.occurrence_id, answer, help_used: help } });
      const next = stage === "pretest"
        ? { ...payloadRef.current, pretestResult: result, pretestAnswer: answer }
        : stage === "recall"
          ? { ...payloadRef.current, recallResult: result, recallAnswer: answer }
          : { ...payloadRef.current, practiceResults: { ...(payloadRef.current.practiceResults || {}), [question.occurrence_id]: result } };
      payloadRef.current = next; setPayload(next); clearTimeout(saveTimer.current); await sendSave(next);
    } catch (e) { setActionError(errorText(e)); }
    finally { setBusy(false); }
  }
  async function gradeReview(cardId, rating) {
    setActionError("");
    await api("/api/cards/" + cardId + "/review", { method: "POST", body: { rating } });
    updatePayload((current) => ({ ...current, reviewIds: [...new Set([...(current.reviewIds || []), cardId])] }));
  }
  async function finish() {
    setActionError(""); setBusy(true);
    try {
      await flush();
      const current = payloadRef.current;
      const result = await api("/api/sessions/" + session.session_id + "/complete", { method: "POST", body: { cards: current.closeCards || [], difficulties: current.difficulties || [] } });
      setSession((value) => ({ ...value, ...result })); setDone(true); await onDone(); window.scrollTo(0, 0);
    } catch (e) { setActionError(errorText(e)); }
    finally { setBusy(false); }
  }
  function saveNote() {
    const draft = payloadRef.current.noteDraft || {};
    if (!draft.text?.trim()) { setActionError("Escreva a anotação antes de guardar."); return; }
    setActionError("");
    updatePayload((current) => ({ ...current, notes: [...(current.notes || []), { id: "note_" + Date.now().toString(36), text: draft.text.trim(), origin: (draft.origin || "").trim(), type: draft.type || "cartão" }], noteDraft: { text: "", origin: "", type: draft.type || "cartão" } }));
  }
  const title = lesson.title;
  if (done) return <div className="completion">
    <div className="completion-mark">✓</div><h1>Aula registrada</h1><p className="muted">{lesson.topic_title} · {title}</p><p>{(payload.closeCards || []).filter((card) => card.selected).length} cartão(ões) criados · progresso atualizado.</p><div className="actions center"><Button onClick={onExit}>Voltar ao roadmap</Button></div>
  </div>;
  return <div className="session-view">
    <div className="session-top"><button className="icon-button exit-button" onClick={async () => { setBusy(true); try { await flush(); await onExit(); } catch (e) { setActionError(errorText(e)); } finally { setBusy(false); } }} aria-label="Salvar e sair da sessão">×</button>
      <div className="step-progress" aria-label={"Etapa " + (step + 1) + " de 6"}>{STEPS.map((item, index) => <span key={item.title} className={index < step ? "passed" : index === step ? "current" : ""} title={item.title} />)}</div>
      <span className="timer">{Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, "0")}</span>
      <button className="timer-pause" onClick={togglePause} disabled={busy}>{session.timer?.paused ? "Retomar" : "Pausar"}</button>
    </div>
    <div className="session-heading"><p className="muted eyebrow">{lesson.subject_name} · {lesson.topic_title} · {title}</p><h1>{STEPS[step].title}</h1><p className="hint"><span>{STEPS[step].hint}</span></p></div>
    <p className="save-state" aria-live="polite">{saveStatus === "saving" ? "Salvando…" : saveStatus === "error" ? "Falha ao salvar" : "Salvo automaticamente"}{saveError && <span> · {saveError}</span>}</p>
    {actionError && <Notice kind="error" onClose={() => setActionError("")}>{actionError}</Notice>}
    {payload.questionPool?.length > 0 && <p className="muted session-pool-note">{payload.questionPool.length} conteúdos nesta sessão · {lesson.questions.length} ocorrências vinculadas à aula. {payload.poolStrategy}</p>}
    {step === 0 && <>
      <label className="field card-field"><span>Despejo livre</span><textarea value={payload.recallText || ""} onChange={(e) => updatePayload({ recallText: e.target.value })} placeholder="O que você lembra da aula anterior…" /></label>
      <div className="section-title"><h2>Cartões vencidos</h2><span className="muted">{nextReview ? "Revisão pendente" : "Dia de hoje"}</span></div>
      {nextReview ? <ReviewCard key={nextReview.card_id} card={nextReview} onGrade={gradeReview} /> : <div className="empty compact"><strong>{dueCards.length ? "Revisões concluídas." : "Nenhum cartão vencido."}</strong><span>{dueCards.length ? "Todos os cartões vencidos foram avaliados." : "Os cartões criados ao fechar uma aula aparecem aqui na data prevista."}</span></div>}
      <div className="section-title"><h2>Questão de recuperação</h2><span className="muted">Outra questão vinculada</span></div>
      {recallQuestion ? <QuestionCard question={recallQuestion} result={payload.recallResult} pending={busy} onSubmit={(answer) => submitAnswer("recall", recallQuestion, answer)} /> : <div className="empty compact"><strong>Não há outra questão vinculada a esta aula.</strong><span>Vincule pelo menos duas ocorrências se quiser uma questão de recuperação além do pré-teste.</span></div>}
    </>}
    {step === 1 && <>
      {!pretestQuestion ? <div className="empty"><strong>Esta aula ainda não tem questões vinculadas.</strong><span>O pré-teste fica vazio até você selecionar uma ocorrência no catálogo.</span><Button secondary onClick={() => onExit("lesson")}>Selecionar questões da aula</Button></div> : <>
        <div className="tag-row"><span className="tag">Pré-instrução</span><span className="muted">Uma questão vinculada à aula</span></div>
        <QuestionCard question={pretestQuestion} result={payload.pretestResult} pending={busy} variant="pretest" onSubmit={(answer) => submitAnswer("pretest", pretestQuestion, answer)} />
      </>}
    </>}
    {step === 2 && <>
      <SyllabusDetails unit={lesson.roadmap} />
      <section className="card study-materials"><h2>Material desta aula</h2>
        {lesson.materials.length ? lesson.materials.map((material) => <div className="material-row" key={material.material_id}>
          <span className="material-symbol">{material.document_id ? "PDF" : "↗"}</span><div className="grow"><strong>{material.title}</strong><span className="muted">{material.document_id ? "Biblioteca local" : material.url}</span></div>
          <a className="button secondary small" href={material.open_url} target="_blank" rel="noreferrer">Abrir</a>
        </div>) : <div className="empty compact"><strong>Sem materiais nesta aula.</strong><span>Você pode voltar depois e adicionar links ou PDFs da biblioteca.</span></div>}
      </section>
      {payload.pretestResult && <div className="feedback"><strong>Gabarito do pré-teste: {payload.pretestResult.snapshot.reference_answer || "sem correção automática"}.</strong><span>Sem comentário; use a aula para revisar a questão.</span></div>}
      <section className="card note-editor"><h2>Anotar durante o estudo</h2>
        <label className="field"><span>Texto</span><textarea className="short-textarea" value={payload.noteDraft?.text || ""} onChange={(e) => updatePayload({ noteDraft: { ...(payloadRef.current.noteDraft || {}), text: e.target.value } })} placeholder="O que vale guardar?" /></label>
        <div className="form-grid"><label className="field grow"><span>Origem</span><input value={payload.noteDraft?.origin || ""} onChange={(e) => updatePayload({ noteDraft: { ...(payloadRef.current.noteDraft || {}), origin: e.target.value } })} placeholder="Vídeo 12:40 ou página 14" /></label><label className="field"><span>Tipo</span><select value={payload.noteDraft?.type || "cartão"} onChange={(e) => updatePayload({ noteDraft: { ...(payloadRef.current.noteDraft || {}), type: e.target.value } })}><option value="cartão">Cartão</option><option value="diagrama">Diagrama</option><option value="dúvida">Dúvida</option></select></label></div>
        <div className="actions"><Button onClick={saveNote}>Guardar anotação</Button></div>
        {payload.notes?.length > 0 && <div className="notes-list">{payload.notes.map((note) => <div className="note-row" key={note.id}><div><p>{note.text}</p><span className="muted">{note.type}{note.origin ? " · " + note.origin : ""}</span></div><button className="icon-button" aria-label="Remover anotação" onClick={() => updatePayload((current) => ({ ...current, notes: current.notes.filter((item) => item.id !== note.id) }))}>×</button></div>)}</div>}
      </section>
    </>}
    {step === 3 && <>
      {lesson.reference_scene && <div className="reference-control"><span className="muted">Há uma referência salva para esta aula.</span><Button secondary small onClick={() => setShowReference((value) => !value)}>{showReference ? "Ocultar comparação" : "Comparar com a aula"}</Button></div>}
      {lesson.reference_scene && showReference && <section className="reference-panel"><div><strong>Referência da aula</strong><span className="muted">Comparação visual, sem nota ou avaliação automática.</span></div><ExcalScene scene={lesson.reference_scene} theme={theme} readOnly label="Quadro de referência da aula" /></section>}
      <section className="card board-card"><div className="board-heading"><div><h2>Reconstrução de memória</h2><p className="muted">Use ferramentas de desenho, texto e formas do Excalidraw. A cena salva permanece editável.</p></div><span className="tag">Quadro editável</span></div>
        <ExcalScene scene={payload.boardScene} theme={theme} onChange={(scene) => updatePayload({ boardScene: scene })} label="Quadro de estudo Excalidraw" />
      </section>
    </>}
    {step === 4 && <>
      {!practiceQuestions?.length ? <div className="empty"><strong>Sem questões objetivas nesta seleção.</strong><span>Abra a aula para consultar a coleção e as propostas discursivas disponíveis.</span><Button secondary onClick={() => onExit("lesson")}>Ver questões da aula</Button></div> : <>
        <div className="question-selector">{practiceQuestions.map((question, index) => <Chip key={question.occurrence_id} active={(payload.questionIndex || 0) === index} onClick={() => updatePayload({ questionIndex: index })}>Questão {index + 1}</Chip>)}</div>
        <QuestionCard question={currentQuestion} result={payload.practiceResults?.[currentQuestion?.occurrence_id]} pending={busy} helpUsed={Boolean(payload.helpByOccurrence?.[currentQuestion?.occurrence_id])} onHelpChange={(value) => updatePayload((current) => ({ ...current, helpByOccurrence: { ...(current.helpByOccurrence || {}), [currentQuestion.occurrence_id]: value } }))} onSubmit={(answer) => submitAnswer("practice", currentQuestion, answer, Boolean(payload.helpByOccurrence?.[currentQuestion.occurrence_id]))} />
      </>}
    </>}
    {step === 5 && <>
      <section className="card close-card"><div className="section-title"><h2>Escolha notas para virar cartões</h2><span className="muted">Seleção explícita</span></div>
        {(payload.closeCards || []).length ? <div className="close-notes">{payload.closeCards.map((card) => <div className="close-note" key={card.id}>
          <label className="check-line"><input type="checkbox" checked={Boolean(card.selected)} onChange={(e) => updatePayload((current) => ({ ...current, closeCards: current.closeCards.map((item) => item.id === card.id ? { ...item, selected: e.target.checked } : item) }))} />Incluir esta nota</label>
          <div className="form-grid"><label className="field grow"><span>Pergunta</span><textarea className="short-textarea" value={card.front} onChange={(e) => updatePayload((current) => ({ ...current, closeCards: current.closeCards.map((item) => item.id === card.id ? { ...item, front: e.target.value } : item) }))} /></label><label className="field grow"><span>Resposta</span><textarea className="short-textarea" value={card.back} onChange={(e) => updatePayload((current) => ({ ...current, closeCards: current.closeCards.map((item) => item.id === card.id ? { ...item, back: e.target.value } : item) }))} placeholder="Escreva a resposta do cartão" /></label></div>
          <label className="field"><span>Dificuldade que deseja rever (opcional)</span><input value={card.difficulty} onChange={(e) => updatePayload((current) => ({ ...current, closeCards: current.closeCards.map((item) => item.id === card.id ? { ...item, difficulty: e.target.value } : item) }))} placeholder="Ex.: distinguir exceções" /></label>
        </div>)}</div> : <div className="empty compact"><strong>Você não guardou anotações nesta aula.</strong><span>É possível concluir sem criar cartões.</span></div>}
      </section>
      <section className="card close-card"><div className="section-title"><h2>Dificuldades</h2><span className="muted">Registro desta aula</span></div>
        <div className="form-grid"><label className="field grow"><span>O que ainda ficou difícil?</span><input value={difficultyDraft} onChange={(e) => setDifficultyDraft(e.target.value)} placeholder="Escreva uma dificuldade" /></label><Button secondary disabled={!difficultyDraft.trim()} onClick={() => { updatePayload((current) => ({ ...current, difficulties: [...(current.difficulties || []), difficultyDraft.trim()] })); setDifficultyDraft(""); }}>Adicionar</Button></div>
        {payload.difficulties?.length > 0 && <div className="difficulty-list">{payload.difficulties.map((value, index) => <div className="difficulty-item" key={index}><span>{value}</span><button className="icon-button" aria-label="Remover dificuldade" onClick={() => updatePayload((current) => ({ ...current, difficulties: current.difficulties.filter((_, i) => i !== index) }))}>×</button></div>)}</div>}
        <p className="muted schedule-note">Cartões novos: primeira revisão amanhã; depois de 1, 3 e 7 dias.</p>
      </section>
    </>}
    <div className="session-actions">
      <Button secondary disabled={busy || step === 0} onClick={() => navigate(step - 1)}>Voltar</Button><span className="spacer" />
      {step < 5 ? <Button disabled={busy} onClick={() => navigate(step + 1)}>{busy ? "Salvando…" : step === 4 ? "Ir para Fechar" : "Continuar"}</Button>
        : <Button disabled={busy || (payload.closeCards || []).some((card) => card.selected && (!card.front.trim() || !card.back.trim()))} onClick={finish}>{busy ? "Registrando…" : "Registrar aula"}</Button>}
    </div>
    <p className="muted duration-note">Duração sugerida: {STEPS[step].minutes} min. O cronômetro não bloqueia a etapa.</p>
  </div>;
}

function FreeQuestions() {
  const [question, setQuestion] = useState(null);
  const [result, setResult] = useState(null);
  const [help, setHelp] = useState(false);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  async function loadHistory() {
    const data = await api("/api/attempts/history"); setHistory(data.items || []);
  }
  useEffect(() => { loadHistory().catch((e) => setError(errorText(e))); }, []);
  async function submit(answer) {
    setError(""); setSaving(true);
    try { const outcome = await api("/api/attempts", { method: "POST", body: { occurrence_id: question.occurrence_id, answer, help_used: help } }); setResult(outcome); await loadHistory(); }
    catch (e) { setError(errorText(e)); }
    finally { setSaving(false); }
  }
  return <>
    <div className="page-heading"><div><h1>Questões livres</h1><p className="muted">Sem roteiro. Filtre o catálogo e pare quando quiser.</p></div></div>
    {error && <Notice kind="error" onClose={() => setError("")}>{error}</Notice>}
    {question && <section className="free-selected"><div className="selected-heading"><div><span className="tag">Questão selecionada</span><h2>{question.bank} · {question.contest}{question.number ? " · nº " + question.number : ""}</h2></div><Button secondary small onClick={() => { setQuestion(null); setResult(null); setHelp(false); }}>Fechar questão</Button></div>
      <QuestionCard key={question.occurrence_id + String(Boolean(result))} question={question} result={result} helpUsed={help} onHelpChange={setHelp} onSubmit={submit} pending={saving} />
      {result && <div className="actions"><Button secondary onClick={() => { setResult(null); setHelp(false); }}>Tentar novamente</Button></div>}
    </section>}
    <CatalogBrowser mode="free" initialEligible selectedIds={[]} onChoose={(item) => { setQuestion(item); setResult(null); setHelp(false); window.scrollTo(0, 0); }} />
    <section className="history-section"><div className="section-title"><h2>Histórico de tentativas</h2><span className="muted">{history.length} recentes</span></div>
      {history.length ? <div className="history-list">{history.map((item) => <div className="history-row" key={item.attempt_id}><span className={item.correct === 1 ? "history-mark correct" : item.correct === 0 ? "history-mark incorrect" : "history-mark"}>{item.correct === 1 ? "✓" : item.correct === 0 ? "×" : "·"}</span><div className="grow"><strong>{item.answer}</strong><span className="muted">{new Date(item.created_at).toLocaleString("pt-BR")} · {item.reference_snapshot?.state || "sem referência"}{item.help_used ? " · usou ajuda" : ""}</span></div><span className="muted">{item.correct === null ? "Sem avaliação" : item.correct ? "Certa" : "Errada"}</span></div>)}</div> : <div className="empty compact"><strong>Sem tentativas registradas.</strong><span>As respostas enviadas pelo catálogo ficam neste histórico local.</span></div>}
    </section>
  </>;
}

export default function App() {
  const [data, setData] = useState(null);
  const [screen, setScreen] = useState({ name: "roadmap" });
  const [theme, setTheme] = useState(() => localStorage.getItem("study-theme") || (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  const [loading, setLoading] = useState(true);
  const [globalError, setGlobalError] = useState("");
  const [profileBusy, setProfileBusy] = useState(false);
  async function changeProfile(id) {
    const next = await api("/api/bootstrap", { headers: { "X-Study-Profile": id } });
    selectProfile(id);
    setScreen({ name: "roadmap" });
    setData(next);
    setGlobalError("");
  }
  async function switchProfile(id) {
    setProfileBusy(true);
    try { await changeProfile(id); }
    finally { setProfileBusy(false); }
  }
  async function createProfile(name) {
    setProfileBusy(true);
    try {
      const profile = await api("/api/profiles", { method: "POST", body: { name } });
      await changeProfile(profile.id);
    } finally { setProfileBusy(false); }
  }
  async function refresh() {
    const next = await api("/api/bootstrap"); setData(next); return next;
  }
  useEffect(() => {
    let active = true;
    api("/api/bootstrap").then((result) => {
      if (!active) return;
      setData(result);
      if (result.active_session) openSession(result.active_session);
    }).catch((e) => setGlobalError(errorText(e))).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("study-theme", theme); }, [theme]);
  async function createTopic(subject, title) {
    await api("/api/topics", { method: "POST", body: { subject, title } }); await refresh();
  }
  async function createLesson(topic_id, title) {
    const result = await api("/api/lessons", { method: "POST", body: { topic_id, title } }); await refresh(); return result;
  }
  async function openSession(session) {
    try {
      const lesson = await api("/api/lessons/" + session.lesson_id);
      setScreen({ name: "session", session, lesson }); setGlobalError("");
    } catch (e) { setGlobalError(errorText(e)); }
  }
  async function startSession(lessonId) {
    setGlobalError("");
    try { const session = await api("/api/lessons/" + lessonId + "/sessions", { method: "POST", body: {} }); await refresh(); await openSession(session); }
    catch (e) { setGlobalError(errorText(e)); }
  }
  const topicRoute = screen.name === "topic" ? data?.subjects.flatMap((subject) => subject.topics.map((topic) => ({ subject, topic }))).find((item) => item.topic.id === screen.topicId) : null;
  return <div className="app-shell">
    <header className="app-header"><button className="brand" disabled={screen.name === "session"} onClick={() => setScreen({ name: "roadmap" })} aria-label="Abrir roadmap"><span className="brand-mark">e</span><span>Estudo</span></button>
      {screen.name !== "session" && <nav className="main-nav" aria-label="Navegação principal"><button className={screen.name !== "free" ? "selected" : ""} onClick={() => setScreen({ name: "roadmap" })}>Roadmap</button><button className={screen.name === "free" ? "selected" : ""} onClick={() => setScreen({ name: "free" })}>Questões livres</button></nav>}
      <button className="theme-toggle" onClick={() => setTheme((value) => value === "dark" ? "light" : "dark")} aria-label={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}>{theme === "dark" ? "☼" : "◐"}</button>
    </header>
    {data && <ProfileBox data={data} disabled={screen.name === "session"} busy={profileBusy} onSelect={switchProfile} onCreate={createProfile} />}
    <main key={data?.profile.id} inert={profileBusy ? "" : undefined} className={screen.name === "session" ? "content session-content" : "content"}>
      {globalError && <Notice kind="error" onClose={() => setGlobalError("")}>{globalError}</Notice>}
      {loading && !data ? <div className="empty loading-state"><strong>Abrindo o espaço de estudo…</strong></div> : null}
      {data && screen.name === "roadmap" && <Roadmap data={data} onOpenTopic={(subject, topic) => setScreen({ name: "topic", topicId: topic.id })} onResume={() => openSession(data.active_session)} onCreateTopic={createTopic} onOpenLesson={(lessonId) => setScreen({ name: "lesson", lessonId })} onStart={startSession} onRefresh={refresh} />}
      {data && screen.name === "topic" && topicRoute && <TopicPage subject={topicRoute.subject} topic={topicRoute.topic} onBack={() => setScreen({ name: "roadmap" })} onOpenLesson={(lessonId) => setScreen({ name: "lesson", lessonId })} onCreateLesson={createLesson} onRefresh={refresh} />}
      {screen.name === "lesson" && <LessonEditor lessonId={screen.lessonId} onBack={() => { refresh().catch(() => {}); setScreen({ name: "topic", topicId: data?.subjects.flatMap((s) => s.topics).find((t) => t.lessons.some((l) => l.id === screen.lessonId))?.id || "" }); }} onStart={() => startSession(screen.lessonId)} onRefresh={refresh} theme={theme} />}
      {screen.name === "free" && <FreeQuestions />}
      {screen.name === "session" && <StudySession initialSession={screen.session} lesson={screen.lesson} theme={theme} onExit={async (destination) => { await refresh(); setScreen(destination === "lesson" ? { name: "lesson", lessonId: screen.lesson.lesson_id } : { name: "roadmap" }); }} onDone={refresh} />}
      {data && screen.name === "topic" && !topicRoute && <div className="empty"><strong>Tópico não encontrado.</strong><Button secondary onClick={() => setScreen({ name: "roadmap" })}>Voltar ao roadmap</Button></div>}
    </main>
    <footer className="app-footer"><span>Dados salvos neste computador</span></footer>
  </div>;
}
