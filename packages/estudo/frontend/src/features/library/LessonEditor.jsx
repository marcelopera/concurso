import React, { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Button, Notice, errorText } from "../../components/ui";
import { SyllabusDetails } from "../roadmap/RoadmapPlan";
import { LinkedQuestionList } from "../catalog/QuestionLinks";
import { CatalogBrowser } from "../catalog/Questions";
import { SceneEditor } from "../whiteboard/Whiteboard";

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

function LessonEditor({ lessonId, onBack, onStart, theme }) {
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
  const reload = useCallback(async () => {
    const result = await api("/api/lessons/" + lessonId);
    setLesson(result); setTitle(result.title); setSelected(result.occurrence_ids || []);
  }, [lessonId]);
  useEffect(() => { reload().catch((e) => setError(errorText(e))); }, [reload]);
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
      {lesson.occurrence_ids.length > lesson.questions.length && <Notice kind="error">{lesson.occurrence_ids.length - lesson.questions.length} vínculo(s) não estão no catálogo atual. Para recuperá-los, use o catálogo com os IDs originais.</Notice>}
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
      <CatalogBrowser mode="select" initialEligible={false} selectedIds={selected} onToggle={(item) => setSelected((ids) => ids.includes(item.occurrence_id) ? ids.filter((id) => id !== item.occurrence_id) : [...ids, item.occurrence_id])} />
      <div className="actions"><Button secondary onClick={() => setPicker(false)}>Cancelar</Button><Button disabled={saving} onClick={async () => { if (await saveQuestions()) setPicker(false); }}>Salvar seleção ({selected.length})</Button></div>
    </section></div>}
    {library && <LibraryPicker onClose={() => setLibrary(false)} onChoose={(item) => addMaterial({ title: item.nome || item.titulo || item.concurso || "PDF", document_id: item.documento_id })} />}
    {referenceEditor && <SceneEditor theme={theme} scene={lesson.reference_scene} onClose={() => setReferenceEditor(false)} onSave={saveReference} />}
  </>;
}

export default LessonEditor;
