import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Button, Notice, errorText } from "../../components/ui";
import { QuestionResult } from "./Questions";

export default function Exams({ profileId }) {
  const key = "study-exam-" + profileId;
  const [exams, setExams] = useState([]);
  const [draft, setDraft] = useState(() => {
    try { return JSON.parse(localStorage.getItem(key)) || null; } catch { return null; }
  });
  const [questions, setQuestions] = useState(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    api("/api/exams").then((data) => { if (live) setExams(data.items); }).catch((e) => { if (live) setError(errorText(e)); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    if (!draft?.examId) { setQuestions(null); return; }
    let live = true;
    api("/api/exams/questions?id=" + encodeURIComponent(draft.examId)).then((data) => { if (live) setQuestions(data.items); }).catch((e) => { if (live) setError(errorText(e)); });
    return () => { live = false; };
  }, [draft?.examId]);
  function save(next) {
    if (next) localStorage.setItem(key, JSON.stringify(next)); else localStorage.removeItem(key);
    setDraft(next);
  }
  function start(exam) {
    setError(""); setIndex(0);
    save({ examId: exam.id, title: exam.title || exam.contest || "Prova", answers: {}, results: {}, finishing: false, completed: false });
  }
  async function finish() {
    let next = { ...draft, finishing: true };
    save(next); setBusy(true); setError("");
    try {
      for (const question of questions) {
        const id = question.occurrence_id;
        if (!next.answers[id]?.trim() || next.results[id]) continue;
        const result = await api("/api/attempts", { method: "POST", headers: { "X-Study-Profile": profileId }, body: { occurrence_id: id, answer: next.answers[id] } });
        next = { ...next, results: { ...next.results, [id]: result } };
        save(next);
      }
      save({ ...next, completed: true });
    } catch (e) { setError(errorText(e)); }
    finally { setBusy(false); }
  }
  const question = questions?.[index];
  const answered = Object.values(draft?.answers || {}).filter((answer) => answer.trim()).length;
  const results = Object.values(draft?.results || {});
  return <>
    <div className="page-heading"><div><h1>Provas completas</h1><p className="muted">Responda às questões de uma prova e veja a correção ao finalizar.</p></div></div>
    {error && <Notice kind="error" onClose={() => setError("")}>{error}</Notice>}
    {!draft && <section className="catalog-list">
      {exams.map((exam) => <article className="catalog-item" key={exam.id}><div className="catalog-item-copy"><strong>{exam.title || "Prova sem título"}</strong><p>{[exam.contest, exam.bank, exam.booklet].filter(Boolean).join(" · ")}</p><span className="muted">{exam.question_count} {exam.question_count === 1 ? "questão disponível" : "questões disponíveis"}</span></div><Button small disabled={!exam.question_count} onClick={() => start(exam)}>Iniciar simulado</Button></article>)}
      {!exams.length && <div className="empty compact"><strong>Nenhuma prova encontrada.</strong><span>As provas disponíveis no catálogo aparecerão aqui.</span></div>}
    </section>}
    {draft && <section>
      <div className="selected-heading"><div><h2>{draft.title}</h2><span className="muted">{questions ? `${answered} de ${questions.length} respondidas` : "Carregando questões…"}</span></div><Button secondary small disabled={busy} onClick={() => { if (draft.completed || window.confirm("Sair e descartar este simulado?")) { save(null); setIndex(0); setError(""); } }}>Voltar às provas</Button></div>
      {draft.completed && <div className="feedback"><strong>Simulado concluído</strong><span>{results.filter((r) => r.correct === true).length} acertos · {results.filter((r) => r.correct === false).length} erros · {results.filter((r) => r.correct === null).length} sem correção automática · {questions ? questions.length - answered : 0} em branco</span></div>}
      {draft.finishing && !draft.completed && <div className="feedback"><strong>Correção em andamento</strong><span>Se houve uma falha, continue para corrigir as respostas restantes.</span><Button disabled={busy || !questions} onClick={finish}>{busy ? "Corrigindo…" : "Continuar correção"}</Button></div>}
      {question && <div className="card question-card">
        <p className="muted">Questão {index + 1} de {questions.length}{question.number ? " · nº " + question.number : ""}{question.discipline ? " · " + question.discipline : ""}</p>
        {question.contexts?.map((context, i) => <details className="context" key={i}><summary>Texto-base {i + 1}</summary><p>{context}</p></details>)}
        {question.source_document_id && <a className="question-source" href={"/api/library/file?document_id=" + encodeURIComponent(question.source_document_id) + (question.pages?.[0] ? "#page=" + question.pages[0] : "")} target="_blank" rel="noreferrer">Fonte original · PDF</a>}
        <p className="question-stem">{question.stem}</p>
        {question.alternatives?.length ? <div className="options">{question.alternatives.map((choice) => <button key={choice.label} className={"option" + (draft.answers[question.occurrence_id] === choice.label ? " exam-option-selected" : "")} aria-pressed={draft.answers[question.occurrence_id] === choice.label} disabled={draft.finishing} onClick={() => save({ ...draft, answers: { ...draft.answers, [question.occurrence_id]: choice.label } })}><b>{choice.label}</b><span>{choice.text}</span></button>)}</div> : <label className="field"><span>Sua resposta</span><textarea value={draft.answers[question.occurrence_id] || ""} disabled={draft.finishing} maxLength={4000} onChange={(e) => save({ ...draft, answers: { ...draft.answers, [question.occurrence_id]: e.target.value } })} /></label>}
        {draft.completed && (draft.results[question.occurrence_id] ? <QuestionResult result={draft.results[question.occurrence_id]} /> : <p className="muted">Questão deixada em branco.</p>)}
      </div>}
      {questions && <div className="pagination"><Button secondary disabled={index <= 0 || busy} onClick={() => setIndex(index - 1)}>Anterior</Button><span className="muted">{index + 1} / {questions.length}</span><Button secondary disabled={index >= questions.length - 1 || busy} onClick={() => setIndex(index + 1)}>Próxima</Button></div>}
      {questions && !draft.finishing && <div className="actions"><Button disabled={busy} onClick={() => { if (window.confirm(`Finalizar o simulado com ${questions.length - answered} questão(ões) em branco?`)) finish(); }}>Finalizar simulado</Button></div>}
    </section>}
  </>;
}
