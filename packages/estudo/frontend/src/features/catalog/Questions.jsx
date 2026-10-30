import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Button, Chip, Notice, errorText } from "../../components/ui";
import { MappingEvidence } from "./QuestionLinks";

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

export { QuestionCard, QuestionResult, CatalogBrowser };
