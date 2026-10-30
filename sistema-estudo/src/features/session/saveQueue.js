// The newest response alone updates the screen; all writes stay in order.
export function createSaveQueue(save, onStatus) {
  let chain = Promise.resolve();
  let version = 0;
  return {
    markDirty() {
      version++;
      onStatus("saving");
    },
    enqueue(value) {
      const current = ++version;
      onStatus("saving");
      const task = chain.catch(() => {}).then(() => save(value));
      chain = task;
      return task.then(
        (saved) => {
          if (current === version) onStatus("saved", saved);
          return saved;
        },
        (error) => {
          if (current === version) onStatus("error", error);
          throw error;
        },
      );
    },
  };
}
