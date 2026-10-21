export type Route = 'home' | 'quoridor';
export function routeFromHash(hash: string): Route {
  return hash === '#/quoridor' || hash === '#/quoridor/' ? 'quoridor' : 'home';
}

type NavigationPorts = {
  hash(): string;
  home(warning?: string): void;
  loading(): HTMLElement;
  load(): Promise<{
    mountQuoridor(root: HTMLElement, signal: AbortSignal): { exitWarning(): string | undefined };
  }>;
  failed(error: unknown): void;
};

// Every route owns one abort scope, including the time spent waiting for its import.
export function createNavigation(ports: NavigationPorts): {
  update(): Promise<void>;
  dispose(): void;
} {
  let active: AbortController | undefined;
  let current: Route | undefined;
  let game: { exitWarning(): string | undefined } | undefined;
  return {
    async update() {
      const route = routeFromHash(ports.hash());
      if (route === current) return;
      current = route;
      active?.abort();
      const warning = game?.exitWarning();
      game = undefined;
      const lifetime = new AbortController();
      active = lifetime;
      if (route === 'home') {
        ports.home(warning);
        return;
      }
      const root = ports.loading();
      try {
        const module = await ports.load();
        if (lifetime.signal.aborted) return;
        game = module.mountQuoridor(root, lifetime.signal);
      } catch (error) {
        if (lifetime.signal.aborted) return;
        lifetime.abort();
        ports.failed(error);
      }
    },
    dispose() {
      active?.abort();
      current = undefined;
    },
  };
}
