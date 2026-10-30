import React, { useRef, useState } from 'react';
import { api } from './api';

export default function ProfileBox({ data, disabled, busy, onSelect, onCreate }) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  async function run(action) {
    setError('');
    try { await action(); setCreating(false); setName(''); }
    catch (err) { setError(err.message); }
  }
  return <section className="card profile-box" aria-label="Perfil de estudo">
    <div className="profile-controls">
      <span className="profile-avatar" aria-hidden="true">{data.profile.name.slice(0, 1).toLocaleUpperCase('pt-BR')}</span>
      <label className="field grow"><span>Perfil de estudo</span><select aria-label="Perfil de estudo" disabled={disabled || busy} value={data.profile.id} onChange={(e) => run(() => onSelect(e.target.value))}>
        {data.profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select></label>
      <button className="button secondary small" disabled={disabled || busy} onClick={() => { setCreating(!creating); setError(''); }}>{creating ? 'Cancelar' : '+ Criar perfil'}</button>
    </div>
    <p className="muted">{disabled ? 'Saia da sessão para trocar ou criar um perfil.' : busy ? 'Abrindo perfil…' : 'Seu progresso é salvo automaticamente neste perfil, neste computador.'}</p>
    {creating && !disabled && <form className="profile-create" onSubmit={(e) => { e.preventDefault(); run(() => onCreate(name)); }}>
      <label className="field grow"><span>Nome do perfil</span><input autoFocus required maxLength={60} value={name} disabled={busy} onChange={(e) => setName(e.target.value)} placeholder="Ex.: Marcela" /></label>
      <button className="button small" disabled={busy || !name.trim()}>{busy ? 'Criando…' : 'Criar perfil'}</button>
    </form>}
    {error && <p className="notice error" role="alert">{error}</p>}
  </section>;
}

export function ResetRoadmap({ profile, onRefresh }) {
  const dialog = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  async function reset() {
    setBusy(true); setError(''); setMessage('');
    try {
      await api('/api/roadmap/reset', { method: 'POST', body: { confirm: profile.id } });
      await onRefresh();
      dialog.current.close();
      setMessage('O roadmap de ' + profile.name + ' foi resetado. Você pode começar de novo.');
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="roadmap-reset">
    <button className="button secondary small danger" onClick={() => { setError(''); dialog.current.showModal(); }}>Resetar progresso do roadmap</button>
    {message && <p className="notice" role="status">{message}</p>}
    <dialog ref={dialog} className="reset-dialog" aria-labelledby="reset-title" aria-describedby="reset-description" onCancel={(e) => { if (busy) e.preventDefault(); }}>
      <h2 id="reset-title">Resetar o roadmap de {profile.name}?</h2>
      <p id="reset-description">As aulas e atividades voltarão a ficar pendentes. As sessões, respostas, anotações, cartões e revisões gerados nas aulas deste roadmap serão apagados deste perfil.</p>
      <p className="muted">O conteúdo das aulas, os materiais, as questões vinculadas, as questões livres e os outros perfis serão mantidos. Uma cópia de segurança será criada antes do reset.</p>
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="actions"><button autoFocus className="button secondary" disabled={busy} onClick={() => dialog.current.close()}>Cancelar</button><button className="button danger" disabled={busy} onClick={reset}>{busy ? 'Resetando…' : 'Confirmar reset'}</button></div>
    </dialog>
  </div>;
}
