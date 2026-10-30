import React, { useState } from "react";
import { Button, Chip, Notice, errorText } from "../../components/ui";
import { ResetRoadmap } from "../../ProfileBox";
import RoadmapPlan from "../../RoadmapPlan";
import { MappingOverview } from "../../QuestionLinks";

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

export { Roadmap, TopicPage };
