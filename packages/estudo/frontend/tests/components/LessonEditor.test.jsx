import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../src/lib/api.js";
import LessonEditor from "../../src/features/library/LessonEditor.jsx";

vi.mock("../../src/lib/api.js", () => ({
  api: vi.fn(),
  profileHeaders: vi.fn(() => ({})),
}));

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function lesson(id, title) {
  return {
    lesson_id: id,
    title,
    topic_title: "Finanças públicas",
    subject_name: "Administração pública",
    occurrence_ids: [],
    questions: [],
    materials: [],
  };
}

function renderLessonEditor(lessonId) {
  return render(
    <LessonEditor
      lessonId={lessonId}
      onBack={vi.fn()}
      onStart={vi.fn()}
      theme="light"
    />,
  );
}

describe("LessonEditor", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows loading and an error, then retries the lesson request", async () => {
    const failedLoad = deferred();
    api.mockReturnValueOnce(failedLoad.promise);

    renderLessonEditor("lesson-1");
    expect(screen.getByRole("status")).toHaveTextContent("Carregando aula");

    await act(async () => {
      failedLoad.reject(new Error("Conexão indisponível"));
      await failedLoad.promise.catch(() => {});
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Conexão indisponível",
    );
    const user = userEvent.setup();
    api.mockResolvedValueOnce(lesson("lesson-1", "Noções de orçamento"));
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(
      await screen.findByRole("heading", { name: "Configurar aula" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Título")).toHaveValue("Noções de orçamento");
    expect(api).toHaveBeenNthCalledWith(2, "/api/lessons/lesson-1");
  });

  it("switches lessons and ignores a late response for the previous lesson", async () => {
    const firstLoad = deferred();
    const secondLoad = deferred();
    api.mockImplementation((path) =>
      path === "/api/lessons/lesson-a" ? firstLoad.promise : secondLoad.promise,
    );

    const view = renderLessonEditor("lesson-a");
    expect(screen.getByRole("status")).toHaveTextContent("Carregando aula");

    view.rerender(
      <LessonEditor
        lessonId="lesson-b"
        onBack={vi.fn()}
        onStart={vi.fn()}
        theme="light"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Carregando aula");

    await act(async () => {
      secondLoad.resolve(lesson("lesson-b", "Aula atual"));
      await secondLoad.promise;
    });
    expect(screen.getByLabelText("Título")).toHaveValue("Aula atual");

    await act(async () => {
      firstLoad.resolve(lesson("lesson-a", "Aula antiga"));
      await firstLoad.promise;
    });
    expect(screen.getByLabelText("Título")).toHaveValue("Aula atual");
    expect(api).toHaveBeenNthCalledWith(1, "/api/lessons/lesson-a");
    expect(api).toHaveBeenNthCalledWith(2, "/api/lessons/lesson-b");
  });
});
