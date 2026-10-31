import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Button, Notice, errorText } from "../../components/ui";
import { CatalogBrowser, QuestionCard } from "./Questions";

function FreeQuestions() {
  const [question, setQuestion] = useState(null);
  const [result, setResult] = useState(null);
  const [help, setHelp] = useState(false);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  async function loadHistory() {
    const data = await api("/api/attempts/history");
    setHistory(data.items || []);
  }
  useEffect(() => {
    loadHistory().catch((e) => setError(errorText(e)));
  }, []);
  async function submit(answer) {
    setError("");
    setSaving(true);
    try {
      const outcome = await api("/api/attempts", {
        method: "POST",
        body: {
          occurrence_id: question.occurrence_id,
          answer,
          help_used: help,
        },
      });
      setResult(outcome);
      await loadHistory();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Questões livres</h1>
          <p className="muted">
            Sem roteiro. Filtre o catálogo e pare quando quiser.
          </p>
        </div>
      </div>
      {error && (
        <Notice kind="error" onClose={() => setError("")}>
          {error}
        </Notice>
      )}
      {question && (
        <section className="free-selected">
          <div className="selected-heading">
            <div>
              <span className="tag">Questão selecionada</span>
              <h2>
                {question.bank} · {question.contest}
                {question.number ? " · nº " + question.number : ""}
              </h2>
            </div>
            <Button
              secondary
              small
              onClick={() => {
                setQuestion(null);
                setResult(null);
                setHelp(false);
              }}
            >
              Fechar questão
            </Button>
          </div>
          <QuestionCard
            key={question.occurrence_id + String(Boolean(result))}
            question={question}
            result={result}
            helpUsed={help}
            onHelpChange={setHelp}
            onSubmit={submit}
            pending={saving}
          />
          {result && (
            <div className="actions">
              <Button
                secondary
                onClick={() => {
                  setResult(null);
                  setHelp(false);
                }}
              >
                Tentar novamente
              </Button>
            </div>
          )}
        </section>
      )}
      <CatalogBrowser
        mode="free"
        initialEligible
        selectedIds={[]}
        onChoose={(item) => {
          setQuestion(item);
          setResult(null);
          setHelp(false);
          window.scrollTo(0, 0);
        }}
      />
      <section className="history-section">
        <div className="section-title">
          <h2>Histórico de tentativas</h2>
          <span className="muted">{history.length} recentes</span>
        </div>
        {history.length ? (
          <div className="history-list">
            {history.map((item) => (
              <div className="history-row" key={item.attempt_id}>
                <span
                  className={
                    item.correct === 1
                      ? "history-mark correct"
                      : item.correct === 0
                        ? "history-mark incorrect"
                        : "history-mark"
                  }
                >
                  {item.correct === 1 ? "✓" : item.correct === 0 ? "×" : "·"}
                </span>
                <div className="grow">
                  <strong>{item.answer}</strong>
                  <span className="muted">
                    {new Date(item.created_at).toLocaleString("pt-BR")} ·{" "}
                    {item.reference_snapshot?.state || "sem referência"}
                    {item.help_used ? " · usou ajuda" : ""}
                  </span>
                </div>
                <span className="muted">
                  {item.correct === null
                    ? "Sem avaliação"
                    : item.correct
                      ? "Certa"
                      : "Errada"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty compact">
            <strong>Sem tentativas registradas.</strong>
            <span>
              As respostas enviadas pelo catálogo ficam neste histórico local.
            </span>
          </div>
        )}
      </section>
    </>
  );
}

export default FreeQuestions;
