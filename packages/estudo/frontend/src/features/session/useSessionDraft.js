import { useCallback, useEffect, useRef, useState } from "react";
import { api, profileHeaders } from "../../lib/api";
import { errorText } from "../../components/ui";
import { createSaveQueue } from "./saveQueue";

export function useSessionDraft(initialPayload, sessionId, setSession) {
  const [payload, setPayload] = useState(initialPayload);
  const payloadRef = useRef(payload);
  const saveTimer = useRef(null);
  const [saveStatus, setSaveStatus] = useState("saved");
  const [saveError, setSaveError] = useState("");
  const queue = useRef(null);
  if (queue.current === null) {
    queue.current = createSaveQueue(
      (value) => api(`/api/sessions/${sessionId}/state`, { method: "PUT", body: { payload: value } }),
      (status, result) => {
        setSaveStatus(status);
        setSaveError(status === "error" ? errorText(result) : "");
        if (status === "saved") setSession((current) => ({ ...current, ...result }));
      },
    );
  }
  const sendSave = useCallback((value) => queue.current.enqueue(value), []);
  const updatePayload = useCallback((patch) => {
    const previous = payloadRef.current;
    const next = typeof patch === "function" ? patch(previous) : { ...previous, ...patch };
    payloadRef.current = next;
    setPayload(next);
    queue.current.markDirty();
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      saveTimer.current = null;
      sendSave(payloadRef.current).catch(() => {});
    }, 650);
    return next;
  }, [sendSave]);
  const flush = useCallback(() => {
    clearTimeout(saveTimer.current);
    saveTimer.current = null;
    return sendSave(payloadRef.current);
  }, [sendSave]);
  useEffect(() => () => clearTimeout(saveTimer.current), []);
  useEffect(() => {
    function sendPendingSave() {
      const body = JSON.stringify({ payload: payloadRef.current });
      if (new Blob([body]).size > 60000) return false;
      fetch(`/api/sessions/${sessionId}/state`, {
        method: "PUT", headers: { ...profileHeaders(), "Content-Type": "application/json" },
        body, keepalive: true, credentials: "same-origin",
      }).catch(() => {});
      return true;
    }
    function beforeUnload(event) {
      if (saveStatus === "saved") return;
      if (!sendPendingSave() || saveStatus === "error") { event.preventDefault(); event.returnValue = ""; }
    }
    function pageHide() { if (saveStatus !== "saved") sendPendingSave(); }
    window.addEventListener("beforeunload", beforeUnload);
    window.addEventListener("pagehide", pageHide);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      window.removeEventListener("pagehide", pageHide);
    };
  }, [sessionId, saveStatus]);
  return { payload, setPayload, payloadRef, saveTimer, saveStatus, saveError, sendSave, updatePayload, flush };
}
