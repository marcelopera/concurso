import React, { useEffect, useState } from "react";
import { api } from "../../api";
import { Button, Chip, Notice, errorText } from "../../components/ui";
import { SyllabusDetails } from "../../RoadmapPlan";
import { QuestionCard } from "../catalog/Questions";
import { ExcalScene } from "../whiteboard/Whiteboard";

import ReviewCard from "./ReviewCard";
import { useSessionDraft } from "./useSessionDraft";

function StudySession({ initialSession, lesson, onExit, onDone, theme, steps }) {
  const [session, setSession] = useState(initialSession);
  const draft = useSessionDraft(() => ({
    recallText: "", pretestOccurrenceId: lesson.questions?.[0]?.occurrence_id || "", notes: [], noteDraft: { text: "", origin: "", type: "cartão" },
    boardScene: { elements: [], appState: {}, files: {} }, questionIndex: 0, practiceResults: {}, helpByOccurrence: {}, pretestResult: null,
    closeCards: [], difficulties: [], reviewIds: [], ...(initialSession.payload || {}),
  }), initialSession.session_id, setSession);
  const { payload, setPayload, payloadRef, saveTimer, saveStatus, saveError, sendSave, updatePayload, flush } = draft;
  const [remaining, setRemaining] = useState(initialSession.timer?.remaining_seconds ?? steps[initialSession.current_step].minutes * 60);
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

  useEffect(() => {
    let live = true;
    api("/api/cards/due").then((result) => { if (live) setDueCards(result.items || []); }).catch((e) => { if (live) setActionError(errorText(e)); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    const update = () => {
      const timer = session.timer || {};
      if (timer.paused) { setRemaining(timer.remaining_seconds || 0); return; }
      if (timer.deadline_at) setRemaining(Math.max(0, Math.ceil((Date.parse(timer.deadline_at) - Date.now()) / 1000)));
      else setRemaining(steps[step].minutes * 60);
    };
    update(); const handle = setInterval(update, 500);
    return () => clearInterval(handle);
  }, [session.timer, step, steps]);

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
      <div className="step-progress" aria-label={"Etapa " + (step + 1) + " de " + steps.length}>{steps.map((item, index) => <span key={item.title} className={index < step ? "passed" : index === step ? "current" : ""} title={item.title} />)}</div>
      <span className="timer">{Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, "0")}</span>
      <button className="timer-pause" onClick={togglePause} disabled={busy}>{session.timer?.paused ? "Retomar" : "Pausar"}</button>
    </div>
    <div className="session-heading"><p className="muted eyebrow">{lesson.subject_name} · {lesson.topic_title} · {title}</p><h1>{steps[step].title}</h1><p className="hint"><span>{steps[step].hint}</span></p></div>
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
    <p className="muted duration-note">Duração sugerida: {steps[step].minutes} min. O cronômetro não bloqueia a etapa.</p>
  </div>;
}

export default StudySession;
