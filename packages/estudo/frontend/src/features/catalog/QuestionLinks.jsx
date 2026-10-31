import React, { useMemo, useState } from "react";

export function MappingEvidence({ mapping }) {
  if (!mapping) return null;
  return (
    <details className="mapping-evidence">
      <summary>
        Correspondência {mapping.relation === "direta" ? "direta" : "correlata"}{" "}
        com a aula ·{" "}
        {mapping.method === "leitura-individual"
          ? "revisão individual"
          : "classificação temática sugerida"}
      </summary>
      {mapping.note && <p className="mapping-note">{mapping.note}</p>}
      <p className="muted">
        {mapping.method === "leitura-individual"
          ? "Correspondência conferida individualmente."
          : "Vínculo sugerido por termos do enunciado e das alternativas. Confira a pertinência antes de usar como diagnóstico."}{" "}
        O estado do gabarito é indicado separadamente.
      </p>
      {mapping.evidence?.slice(0, 3).map((e, i) => (
        <blockquote key={i}>
          <span className="muted">
            {e.field === "alternativas" ? "Alternativas" : "Enunciado"} ·
            evidência
          </span>
          <p>{e.text}</p>
        </blockquote>
      ))}
      <details>
        <summary>Trecho correspondente do edital</summary>
        <p>{mapping.syllabus_excerpt}</p>
      </details>
    </details>
  );
}

export function LinkedQuestionList({ questions, selected, onRemove }) {
  const [search, setSearch] = useState("");
  const [onlyCorrectable, setOnlyCorrectable] = useState(false);
  const [page, setPage] = useState(1);
  const matching = useMemo(
    () =>
      questions.filter(
        (q) =>
          selected.includes(q.occurrence_id) &&
          (!onlyCorrectable || q.reference_status?.correctable) &&
          (!search.trim() ||
            [q.bank, q.contest, q.number, q.stem]
              .join(" ")
              .toLocaleLowerCase("pt-BR")
              .includes(search.toLocaleLowerCase("pt-BR"))),
      ),
    [questions, selected, search, onlyCorrectable],
  );
  const pages = Math.max(1, Math.ceil(matching.length / 15));
  const currentPage = Math.min(page, pages);
  const visible = matching.slice((currentPage - 1) * 15, currentPage * 15);
  return (
    <>
      <div className="linked-filters">
        <label className="field grow">
          <span>Buscar questões vinculadas</span>
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Banca, concurso, número ou enunciado"
          />
        </label>
        <label className="check-line">
          <input
            type="checkbox"
            checked={onlyCorrectable}
            onChange={(e) => {
              setOnlyCorrectable(e.target.checked);
              setPage(1);
            }}
          />
          Somente corrigíveis
        </label>
      </div>
      <p className="muted">
        {matching.length} ocorrências ·{" "}
        {new Set(matching.map((q) => q.question_id)).size} conteúdos distintos.{" "}
        {
          questions.filter(
            (q) =>
              selected.includes(q.occurrence_id) &&
              q.reference_status?.correctable,
          ).length
        }{" "}
        com correção automática.
      </p>
      <div className="linked-list">
        {visible.map((q) => (
          <article className="linked-item" key={q.occurrence_id}>
            <div className="linked-question">
              <span className="linked-check">✓</span>
              <div className="grow">
                <strong>
                  {q.bank} · {q.contest}
                  {q.number ? " · nº " + q.number : ""}
                </strong>
                <span className="muted">
                  {q.reference_status?.correctable
                    ? "Gabarito definitivo · corrigível"
                    : "Consulta · confira o estado do gabarito"}
                  {q.mapping
                    ? " · vínculo " + q.mapping.relation
                    : " · seleção manual"}
                </span>
              </div>
              <button
                className="icon-button"
                aria-label="Desvincular questão"
                onClick={() => onRemove(q.occurrence_id)}
              >
                ×
              </button>
            </div>
            <details className="linked-preview">
              <summary>Ler enunciado e conferir vínculo</summary>
              <p className="question-stem">{q.stem}</p>
              <MappingEvidence mapping={q.mapping} />
              {q.source_document_id && (
                <a
                  href={
                    "/api/library/file?document_id=" +
                    encodeURIComponent(q.source_document_id) +
                    "#page=" +
                    (q.pages?.[0] || 1)
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir prova original ↗
                </a>
              )}
            </details>
          </article>
        ))}
      </div>
      {!visible.length && (
        <p className="muted">Nenhuma questão corresponde aos filtros.</p>
      )}
      {pages > 1 && (
        <div className="pagination">
          <button
            className="button secondary small"
            disabled={currentPage === 1}
            onClick={() => setPage(currentPage - 1)}
          >
            Anterior
          </button>
          <span className="muted">
            Página {currentPage} de {pages}
          </span>
          <button
            className="button secondary small"
            disabled={currentPage === pages}
            onClick={() => setPage(currentPage + 1)}
          >
            Próxima
          </button>
        </div>
      )}
    </>
  );
}

export function MappingOverview({ mapping, onOpenLesson }) {
  if (!mapping) return null;
  return (
    <section className="card mapping-overview">
      <div className="tag-row">
        <span className="tag">Base integrada ao roadmap</span>
        <span className="tag">6 bancas</span>
      </div>
      <h2>Questões para cada aula</h2>
      <p>
        <strong>{mapping.total_occurrences.toLocaleString("pt-BR")}</strong>{" "}
        ocorrências analisadas ·{" "}
        <strong>{mapping.linked_occurrences.toLocaleString("pt-BR")}</strong>{" "}
        compatíveis ·{" "}
        <strong>{mapping.current_links.toLocaleString("pt-BR")}</strong>{" "}
        vínculos em <strong>{mapping.current_lessons_with_questions}</strong>{" "}
        aulas.
      </p>
      <p className="muted">
        Cada vínculo tem evidência e pode ser ajustado na aula. As sessões
        selecionam até 12 conteúdos distintos, priorizando os corrigíveis ainda
        não respondidos. A coleção completa fica em “Ver aula”. Questões
        antigas, pendentes ou sem gabarito definitivo mantêm seus avisos.
      </p>
      <details>
        <summary>Conferir cobertura e lacunas do acervo</summary>
        <p className="muted">
          {mapping.correctable_linked_occurrences} ocorrências vinculadas com
          correção automática. As demais servem para consulta.{" "}
          {mapping.unlinked_occurrences} ocorrências ficaram fora das aulas por
          assunto fora do edital ou ausência de correspondência segura.
          Classificação por regras temáticas com revisão de casos selecionados;
          não houve conferência humana integral.
        </p>
        <div className="mapping-banks">
          {Object.entries(mapping.by_bank).map(([bank, count]) => (
            <span className="tag" key={bank}>
              {bank}: {count.linked}/{count.total}
            </span>
          ))}
        </div>
        {mapping.gaps.length ? (
          <>
            <p className="muted">
              Aulas sem questão compatível identificada nesta base:
            </p>
            {mapping.gaps.map((gap) => (
              <button
                className="backlog-link"
                key={gap.lesson_id}
                onClick={() => onOpenLesson(gap.lesson_id)}
              >
                {gap.title}
              </button>
            ))}
          </>
        ) : (
          <p className="muted">
            Todas as aulas têm ao menos um vínculo. Isso não significa que cada
            subitem do edital esteja coberto pelo acervo.
          </p>
        )}
      </details>
    </section>
  );
}
