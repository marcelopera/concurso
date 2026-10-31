import React, { Suspense, lazy, useCallback, useRef, useState } from "react";
import { Button, Notice, errorText } from "../../components/ui";
const Excalidraw = lazy(() =>
  import("@excalidraw/excalidraw").then((module) => ({
    default: module.Excalidraw,
  })),
);

const TRANSIENT_APP_STATE = new Set([
  "collaborators",
  "activeTool",
  "editingElement",
  "editingGroupId",
  "selectedElementIds",
  "openMenu",
  "openPopup",
  "openSidebar",
  "width",
  "height",
  "offsetTop",
  "offsetLeft",
]);

function serializableAppState(appState) {
  const result = {};
  for (const [key, value] of Object.entries(appState || {})) {
    if (TRANSIENT_APP_STATE.has(key)) continue;
    try {
      JSON.stringify(value);
      result[key] = value;
    } catch {
      /* estado transitório do editor */
    }
  }
  return result;
}

function ExcalScene({
  scene,
  onChange,
  readOnly = false,
  theme = "light",
  label = "Quadro",
}) {
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const apiRef = useRef(null);
  const latestElementsRef = useRef([]);
  const sceneReadyRef = useRef(false);
  const didFitRef = useRef(false);
  const [initialData] = useState(() => ({
    elements: scene?.elements || [],
    appState: {
      viewBackgroundColor: "#ffffff",
      ...serializableAppState(scene?.appState),
      theme,
    },
    files: scene?.files || {},
  }));
  const fitReadOnlyScene = useCallback(() => {
    if (
      !readOnly ||
      didFitRef.current ||
      !sceneReadyRef.current ||
      !apiRef.current
    )
      return;
    didFitRef.current = true;
    const api = apiRef.current;
    const elements = latestElementsRef.current;
    requestAnimationFrame(() =>
      api.scrollToContent(elements, {
        fitToViewport: true,
        viewportZoomFactor: 0.85,
        maxZoom: 1,
        canvasOffsets: { top: 12, right: 12, bottom: 64, left: 12 },
        animate: false,
      }),
    );
  }, [readOnly]);
  const receiveExcalidrawAPI = useCallback(
    (api) => {
      apiRef.current = api;
      fitReadOnlyScene();
    },
    [fitReadOnlyScene],
  );
  const changed = useCallback(
    (elements, appState, files) => {
      latestElementsRef.current = elements || [];
      if (latestElementsRef.current.length > 0) {
        sceneReadyRef.current = true;
        fitReadOnlyScene();
      }
      if (onChangeRef.current)
        onChangeRef.current({
          elements,
          appState: serializableAppState(appState),
          files: files || {},
        });
    },
    [fitReadOnlyScene],
  );
  return (
    <div
      className={"excal-container" + (readOnly ? " read-only" : "")}
      aria-label={label}
    >
      <Suspense fallback={<p>Carregando quadro…</p>}>
        <Excalidraw
          initialData={initialData}
          onChange={changed}
          excalidrawAPI={readOnly ? receiveExcalidrawAPI : undefined}
          viewModeEnabled={readOnly}
          theme={theme}
          langCode="pt-BR"
        />
      </Suspense>
    </div>
  );
}

function SceneEditor({ scene, theme, onSave, onClose }) {
  const [draft, setDraft] = useState(
    scene || { elements: [], appState: {}, files: {} },
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal scene-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Editar quadro de referência"
      >
        <div className="modal-heading">
          <div>
            <h2>Quadro de referência</h2>
            <p className="muted">
              A cena fica vinculada a esta aula e aparece ao comparar durante o
              estudo.
            </p>
          </div>
          <button className="icon-button" aria-label="Fechar" onClick={onClose}>
            ×
          </button>
        </div>
        <ExcalScene
          scene={draft}
          theme={theme}
          onChange={setDraft}
          label="Editor do quadro de referência"
        />
        {error && <Notice kind="error">{error}</Notice>}
        <div className="actions">
          <Button secondary onClick={onClose}>
            Cancelar
          </Button>
          <Button
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              setError("");
              try {
                await onSave(draft);
                onClose();
              } catch (e) {
                setError(errorText(e));
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Salvando…" : "Salvar referência"}
          </Button>
        </div>
      </section>
    </div>
  );
}

export { ExcalScene, SceneEditor };
