import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import StudySession from "../../src/features/session/StudySession.jsx";
import { api } from "../../src/lib/api.js";

vi.mock("../../src/lib/api.js", () => ({
  api: vi.fn(),
  profileHeaders: vi.fn(() => ({})),
}));

function deferred() {
  let resolve;
  const promise = new Promise((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("StudySession", () => {
  it("announces that a draft is saving and when the save completes", async () => {
    const pendingSave = deferred();
    api.mockImplementation((path) => {
      if (path === "/api/cards/due") return Promise.resolve({ items: [] });
      if (path === "/api/sessions/session-1/state") return pendingSave.promise;
      throw new Error(`Unexpected request: ${path}`);
    });

    const user = userEvent.setup();
    const view = render(
      <StudySession
        initialSession={{
          session_id: "session-1",
          current_step: 0,
          status: "active",
          timer: { paused: true, remaining_seconds: 300 },
          payload: {},
        }}
        lesson={{
          lesson_id: "lesson-1",
          title: "Noções de orçamento",
          subject_name: "Administração pública",
          topic_title: "Finanças públicas",
          questions: [],
          materials: [],
        }}
        steps={[
          { title: "Recuperar", hint: "Lembre o que estudou", minutes: 5 },
          { title: "Pré-teste", hint: "Tente responder", minutes: 5 },
          { title: "Estudar", hint: "Revise o conteúdo", minutes: 20 },
          { title: "Praticar", hint: "Resolva questões", minutes: 10 },
          { title: "Refletir", hint: "Registre dificuldades", minutes: 5 },
          { title: "Fechar", hint: "Conclua a aula", minutes: 5 },
        ]}
        onExit={vi.fn()}
        onDone={vi.fn()}
        theme="light"
      />,
    );

    await user.type(screen.getByLabelText("Despejo livre"), "Resumo da aula");
    expect(screen.getByRole("status")).toHaveTextContent("Salvando");

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith(
        "/api/sessions/session-1/state",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    expect(screen.getByRole("status")).toHaveTextContent("Salvando");

    await act(async () => {
      pendingSave.resolve({});
      await pendingSave.promise;
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Salvo automaticamente",
    );

    view.unmount();
  });
});
