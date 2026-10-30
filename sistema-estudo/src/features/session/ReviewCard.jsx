import React, { useState } from "react";
import { Button, Notice, errorText } from "../../components/ui";

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

export default ReviewCard;
