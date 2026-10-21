export type GameRoute = 'quoridor' | 'othello';
export type Route = 'home' | GameRoute;
export function routeFromHash(hash: string): Route {
  if (hash === '#/quoridor' || hash === '#/quoridor/') return 'quoridor';
  if (hash === '#/othello' || hash === '#/othello/') return 'othello';
  return 'home';
}

type NavigationPorts = {
  hash(): string;
  home(warning?: string): void;
  loading(route: GameRoute): HTMLElement;
  load(route: GameRoute): Promise<{
    mount(root: HTMLElement, signal: AbortSignal): { exitWarning(): string | undefined };
  }>;
  failed(error: unknown, route: GameRoute): void;
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
      const root = ports.loading(route);
      try {
        const module = await ports.load(route);
        if (lifetime.signal.aborted) return;
        game = module.mount(root, lifetime.signal);
      } catch (error) {
        if (lifetime.signal.aborted) return;
        lifetime.abort();
        ports.failed(error, route);
      }
    },
    dispose() {
      active?.abort();
      current = undefined;
    },
  };
}
