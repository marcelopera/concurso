import assert from "node:assert/strict";
import { test } from "node:test";
import { createSaveQueue } from "../../src/features/session/saveQueue.js";

test("writes stay in order, and an older response cannot replace the latest state", async () => {
  const pending = [];
  const events = [];
  const queue = createSaveQueue(
    (value) => new Promise((resolve) => pending.push({ value, resolve })),
    (...event) => events.push(event),
  );
  const first = queue.enqueue("first");
  const second = queue.enqueue("second");
  await new Promise(setImmediate);
  assert.deepEqual(pending.map((item) => item.value), ["first"]);
  pending[0].resolve("old response");
  await first;
  await new Promise(setImmediate);
  assert.deepEqual(pending.map((item) => item.value), ["first", "second"]);
  assert.equal(events.some(([status]) => status === "saved"), false);
  pending[1].resolve("new response");
  await second;
  assert.deepEqual(events.at(-1), ["saved", "new response"]);
});

test("a failed save is reported and does not block a subsequent retry", async () => {
  const failure = new Error("offline");
  const events = [];
  const queue = createSaveQueue(
    async (value) => { if (value === "fail") throw failure; return value; },
    (...event) => events.push(event),
  );
  await assert.rejects(queue.enqueue("fail"), /offline/);
  assert.deepEqual(events.at(-1), ["error", failure]);
  assert.equal(await queue.enqueue("retry"), "retry");
  assert.deepEqual(events.at(-1), ["saved", "retry"]);
});
