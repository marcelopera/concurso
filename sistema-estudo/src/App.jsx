import React, { useEffect, useState } from "react";
import { api, selectProfile } from "./api";
import ProfileBox from "./ProfileBox";
import { Button, Notice, errorText } from "./components/ui";
import { Roadmap, TopicPage } from "./features/roadmap/Roadmap";
import LessonEditor from "./features/library/LessonEditor";
import StudySession from "./features/session/StudySession";
import FreeQuestions from "./features/catalog/FreeQuestions";

export default function App() {
  const [data, setData] = useState(null);
  const [screen, setScreen] = useState({ name: "roadmap" });
  const [theme, setTheme] = useState(() => localStorage.getItem("study-theme") || (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  const [loading, setLoading] = useState(true);
  const [globalError, setGlobalError] = useState("");
  const [profileBusy, setProfileBusy] = useState(false);
  async function changeProfile(id) {
    const next = await api("/api/bootstrap", { headers: { "X-Study-Profile": id } });
    selectProfile(id);
    setScreen({ name: "roadmap" });
    setData(next);
    setGlobalError("");
  }
  async function switchProfile(id) {
    setProfileBusy(true);
    try { await changeProfile(id); }
    finally { setProfileBusy(false); }
  }
  async function createProfile(name) {
    setProfileBusy(true);
    try {
      const profile = await api("/api/profiles", { method: "POST", body: { name } });
      await changeProfile(profile.id);
    } finally { setProfileBusy(false); }
  }
  async function refresh() {
    const next = await api("/api/bootstrap"); setData(next); return next;
  }
  useEffect(() => {
    let active = true;
    api("/api/bootstrap").then((result) => {
      if (!active) return;
      setData(result);
      if (result.active_session) openSession(result.active_session);
    }).catch((e) => setGlobalError(errorText(e))).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("study-theme", theme); }, [theme]);
  async function createTopic(subject, title) {
    await api("/api/topics", { method: "POST", body: { subject, title } }); await refresh();
  }
  async function createLesson(topic_id, title) {
    const result = await api("/api/lessons", { method: "POST", body: { topic_id, title } }); await refresh(); return result;
  }
  async function openSession(session) {
    try {
      const lesson = await api("/api/lessons/" + session.lesson_id);
      setScreen({ name: "session", session, lesson }); setGlobalError("");
    } catch (e) { setGlobalError(errorText(e)); }
  }
  async function startSession(lessonId) {
    setGlobalError("");
    try { const session = await api("/api/lessons/" + lessonId + "/sessions", { method: "POST", body: {} }); await refresh(); await openSession(session); }
    catch (e) { setGlobalError(errorText(e)); }
  }
  const topicRoute = screen.name === "topic" ? data?.subjects.flatMap((subject) => subject.topics.map((topic) => ({ subject, topic }))).find((item) => item.topic.id === screen.topicId) : null;
  return <div className="app-shell">
    <header className="app-header"><button className="brand" disabled={screen.name === "session"} onClick={() => setScreen({ name: "roadmap" })} aria-label="Abrir roadmap"><span className="brand-mark">e</span><span>Estudo</span></button>
      {screen.name !== "session" && <nav className="main-nav" aria-label="Navegação principal"><button className={screen.name !== "free" ? "selected" : ""} onClick={() => setScreen({ name: "roadmap" })}>Roadmap</button><button className={screen.name === "free" ? "selected" : ""} onClick={() => setScreen({ name: "free" })}>Questões livres</button></nav>}
      <button className="theme-toggle" onClick={() => setTheme((value) => value === "dark" ? "light" : "dark")} aria-label={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}>{theme === "dark" ? "☼" : "◐"}</button>
    </header>
    {data && <ProfileBox data={data} disabled={screen.name === "session"} busy={profileBusy} onSelect={switchProfile} onCreate={createProfile} />}
    <main key={data?.profile.id} inert={profileBusy ? "" : undefined} className={screen.name === "session" ? "content session-content" : "content"}>
      {globalError && <Notice kind="error" onClose={() => setGlobalError("")}>{globalError}</Notice>}
      {loading && !data ? <div className="empty loading-state"><strong>Abrindo o espaço de estudo…</strong></div> : null}
      {data && screen.name === "roadmap" && <Roadmap data={data} onOpenTopic={(subject, topic) => setScreen({ name: "topic", topicId: topic.id })} onResume={() => openSession(data.active_session)} onCreateTopic={createTopic} onOpenLesson={(lessonId) => setScreen({ name: "lesson", lessonId })} onStart={startSession} onRefresh={refresh} />}
      {data && screen.name === "topic" && topicRoute && <TopicPage subject={topicRoute.subject} topic={topicRoute.topic} onBack={() => setScreen({ name: "roadmap" })} onOpenLesson={(lessonId) => setScreen({ name: "lesson", lessonId })} onCreateLesson={createLesson} onRefresh={refresh} />}
      {screen.name === "lesson" && <LessonEditor lessonId={screen.lessonId} onBack={() => { refresh().catch(() => {}); setScreen({ name: "topic", topicId: data?.subjects.flatMap((s) => s.topics).find((t) => t.lessons.some((l) => l.id === screen.lessonId))?.id || "" }); }} onStart={() => startSession(screen.lessonId)} onRefresh={refresh} theme={theme} />}
      {screen.name === "free" && <FreeQuestions />}
      {screen.name === "session" && <StudySession steps={data.steps} initialSession={screen.session} lesson={screen.lesson} theme={theme} onExit={async (destination) => { await refresh(); setScreen(destination === "lesson" ? { name: "lesson", lessonId: screen.lesson.lesson_id } : { name: "roadmap" }); }} onDone={refresh} />}
      {data && screen.name === "topic" && !topicRoute && <div className="empty"><strong>Tópico não encontrado.</strong><Button secondary onClick={() => setScreen({ name: "roadmap" })}>Voltar ao roadmap</Button></div>}
    </main>
    <footer className="app-footer"><span>Dados salvos neste computador</span></footer>
  </div>;
}
