import React, { useState } from 'react';
import { api } from './api';

export function formatDay(value, long = false) {
  return new Date(value + 'T12:00:00').toLocaleDateString('pt-BR', long
    ? { weekday: 'short', day: '2-digit', month: '2-digit' }
    : { day: '2-digit', month: '2-digit' });
}

export function SyllabusDetails({ unit }) {
  if (!unit) return null;
  return <section className="card syllabus-card">
    <div className="tag-row"><span className="tag">{unit.exam}</span><span className="tag">Meta: {formatDay(unit.scheduled_date)}</span><span className="tag">{unit.minutes} min sugeridos</span></div>
    <h2>Conteúdo desta aula no edital</h2>
    <ul className="syllabus-list">{(unit.checklist || []).map((item, i) => <li key={i}>{item}</li>)}</ul>
    <p className="muted">Ao fechar: recupere os conceitos sem consulta, registre dúvidas e corrija as questões selecionadas. A sessão concluída registra a primeira passagem; use as revisões para aprofundar.</p>
    {unit.source_url && <a href={unit.source_url + (unit.pages?.[0] ? "#page=" + unit.pages[0] : "")} target="_blank" rel="noreferrer">Conferir fonte do plano ↗</a>}
  </section>;
}

export default function RoadmapPlan({ plan, onOpenLesson, onStart, onRefresh }) {
  const initialDay = plan.days.find((d) => d.date >= plan.today)?.date || plan.days.at(-1).date;
  const [selected, setSelected] = useState(initialDay);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const day = plan.days.find((d) => d.date === selected) || plan.days[0];
  const totalMinutes = day.lessons.reduce((sum, u) => sum + u.minutes, 0) + day.activities.reduce((sum, a) => sum + a.minutes, 0);
  async function toggle(activity) {
    setBusy(activity.id); setError('');
    try {
      await api('/api/roadmap/activities/' + activity.id, { method: 'PUT',
        body: { completed: !activity.completed_at, note: activity.note || '' } });
      await onRefresh();
    } catch (err) { setError(err.message); }
    finally { setBusy(''); }
  }
  const weeks = [];
  for (let i = 0; i < plan.days.length; i += 7) weeks.push(plan.days.slice(i, i + 7));
  return <>
    <section className="card plan-hero">
      <div className="tag-row">{plan.board && <span className="tag">{plan.board}</span>}<span className="tag">{plan.title}</span></div>
      <h2>{plan.area}</h2>
      <p>Conteúdo do plano organizado em uma sequência de estudo.</p>
      <div className="plan-metrics"><div><strong>{plan.stats.lessons}</strong><span>aulas do edital</span></div><div><strong>{plan.daily_minutes / 60}h/dia</strong><span>{plan.stats.total_hours} horas no plano</span></div><div><strong>{formatDay(plan.coverage_deadline)}</strong><span>meta de cobertura</span></div><div><strong>{formatDay(plan.exam_date)}</strong><span>prova · {plan.stats.days_remaining} dias</span></div></div>
      <p className="muted">{plan.strategy}</p>
    </section>
    {plan.stats.overdue > 0 && <details className="card overdue-plan"><summary>{plan.stats.overdue} aulas anteriores ainda pendentes · organizar recuperação</summary><p className="muted">O calendário conserva as metas originais. Use o bloco de prática para recuperar atrasos e priorize os conteúdos em que tem mais dificuldade.</p>{plan.overdue_lessons.map((u) => <button key={u.id} className="backlog-link" onClick={() => onOpenLesson(u.id)}>{formatDay(u.scheduled_date)} · {u.subject_name} · {u.title}</button>)}</details>}
    <section className="card daily-plan">
      <div className="section-title"><div><p className="eyebrow muted">PLANO DIÁRIO</p><h2>{formatDay(day.date, true)} · {day.phase}</h2></div><span className="tag">{totalMinutes / 60} horas</span></div>
      <div className="plan-date-control"><button className="button secondary small" disabled={day.date === plan.days[0].date} onClick={() => setSelected(plan.days[plan.days.indexOf(day) - 1].date)}>Anterior</button><label className="field grow" htmlFor="roadmap-date"><span>Dia do plano</span><select id="roadmap-date" aria-label="Dia do plano" value={day.date} onChange={(e) => setSelected(e.target.value)}>{plan.days.map((d) => <option key={d.date} value={d.date}>{formatDay(d.date, true)} · {d.phase}</option>)}</select></label><button className="button secondary small" onClick={() => setSelected(initialDay)}>Hoje</button><button className="button secondary small" disabled={day.date === plan.days.at(-1).date} onClick={() => setSelected(plan.days[plan.days.indexOf(day) + 1].date)}>Próximo</button></div>
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="daily-lessons">{day.lessons.map((unit, i) => <article className="daily-unit" key={unit.id}>
        <span className={'daily-index' + (unit.completed_at ? ' done' : '')}>{unit.completed_at ? '✓' : i + 1}</span><div className="grow"><span className="muted">{unit.subject_name} · {unit.exam} · {unit.minutes} min</span><strong>{unit.title}</strong><span className="muted">{unit.question_count || 0} questões vinculadas · {unit.completed_at ? 'Aula concluída' : 'Sessão de estudo e prática'}</span></div><div className="daily-unit-actions"><button className="button secondary small" onClick={() => onOpenLesson(unit.id)}>Ver aula</button><button className="button small" onClick={() => onStart(unit.id)}>{unit.completed_at ? 'Reestudar' : 'Estudar'}</button></div>
      </article>)}</div>
      {day.activities.map((activity) => <article className="plan-activity" key={activity.id}><label><input type="checkbox" disabled={busy === activity.id} checked={Boolean(activity.completed_at)} onChange={() => toggle(activity)} /><span><strong>{activity.title}</strong><span className="muted">{activity.minutes} min · {activity.completed_at ? 'Concluída' : 'Pendente'}</span></span></label><p className="muted">{activity.detail}</p></article>)}
      {day.review_lessons.length > 0 && <details className="review-targets"><summary>{day.review_lessons.length} aulas previstas para revisão D+1 / D+7 / D+21</summary><p className="muted">Datas calculadas pela meta original. Se estudou em outro dia, ajuste a recuperação pela data real da sessão.</p>{day.review_lessons.map((u) => <button className="backlog-link" key={u.id} onClick={() => onOpenLesson(u.id)}>{u.completed_at ? '✓ ' : 'Ainda pendente · '}{u.subject_name} · {u.title}</button>)}</details>}
    </section>
    <details className="card calendar-plan"><summary>Calendário completo · {formatDay(plan.days[0].date)} a {formatDay(plan.days.at(-1).date)}</summary>{weeks.map((week, i) => <div className="plan-week" key={week[0].date}><h3>Semana {i + 1} · {formatDay(week[0].date)} a {formatDay(week.at(-1).date)}</h3>{week.map((d) => {
      const done = d.lessons.filter((u) => u.completed_at).length + d.activities.filter((a) => a.completed_at).length;
      const total = d.lessons.length + d.activities.length;
      return <button className={'calendar-day' + (d.date === selected ? ' selected' : '')} key={d.date} onClick={() => { setSelected(d.date); document.querySelector('.daily-plan')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}><strong>{formatDay(d.date, true)}</strong><span>{d.lessons.length ? d.lessons.map((u) => u.subject_name.replace('A01 · ', '')).join(' · ') : d.phase}</span><span>{done}/{total} etapas</span></button>;
    })}</div>)}</details>
    <details className="card plan-reference"><summary>Estratégia de prova, marcos e fontes oficiais</summary>
      <p>P1: 80 questões, até 112 pontos. P2: 40 questões A01 × peso 3, até 120 pontos. P3: 1 estudo de caso sobre conhecimentos básicos, até 30 linhas e 120 pontos. P1: 4h pela manhã; P2 e P3 compartilham 4h à tarde.</p>
      <p>Mínimos cumulativos: P1 ≥ 45, P2 ≥ 48, P3 ≥ 48 e P1 + P2 ≥ 116. A correção da discursiva também depende da classificação prevista no edital. Meta de treino sugerida: 75% ou mais nas objetivas, com correção dos erros; essa meta não equivale a nota de corte.</p>
      <p>Nos simulados, selecione os itens da biblioteca ou do catálogo por assunto. Priorize FCC quando houver questões pertinentes e complemente com outras bancas. Os blocos de prática incluem seleção e correção. Os vínculos por aula continuam explícitos.</p>
      <p>Os dois simulados de 8h foram distribuídos em dois dias de 4h, em 21–22/11 e 12–13/12. A data da prova está prevista na retificação 02/2026; confira eventuais novas publicações.</p>
      <ul>{plan.milestones.map((m) => <li key={m.date}><strong>{formatDay(m.date)}/{m.date.slice(0, 4)}</strong> · {m.title}</li>)}</ul>
      <div className="source-list">{plan.sources.map((source) => <a href={source.url} key={source.file} target="_blank" rel="noreferrer">{source.title} ↗</a>)}</div><p className="muted">Fontes conferidas em {formatDay(plan.sources_checked)}/2026. Os agrupamentos e metas de estudo são sugestões; o texto associado a cada aula vem do Anexo II.</p>
    </details>
  </>;
}
