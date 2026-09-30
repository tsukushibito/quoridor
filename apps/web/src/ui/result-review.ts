import { ja } from './strings';
import type { SessionState } from '../session/session-controller';

export function createResultReview(shell: HTMLElement, layout: HTMLElement) {
  const dialog = document.createElement('dialog');
  dialog.id = 'result-dialog'; dialog.className = 'app-dialog result-dialog';
  dialog.setAttribute('aria-labelledby', 'result-heading');
  dialog.setAttribute('aria-describedby', 'result-detail');
  dialog.innerHTML = `<p class="result-eyebrow">${ja.gameFinished}</p><h2 id="result-heading"></h2>
    <p id="result-detail"></p><p id="result-total"></p>
    <div class="result-actions"><button id="result-review" class="accent" type="button" autofocus>${ja.review}</button>
      <button id="result-again" type="button">${ja.playAgain}</button>
      <button id="result-board" class="quiet" type="button">${ja.viewBoard}</button>
      <button id="result-title" class="quiet" type="button">${ja.returnTitle}</button></div>`;
  const actions = document.createElement('footer');
  actions.className = 'action-hud end-hud'; actions.id = 'end-hud'; actions.hidden = true;
  actions.innerHTML = `<div id="finished-actions"><button id="finished-review" class="accent" type="button">${ja.review}</button>
    <button id="finished-result" type="button">${ja.viewResult}</button></div>
    <div id="review-actions" hidden><div class="review-heading"><strong id="review-counter" aria-live="polite"></strong>
      <button id="review-result" type="button">${ja.backToResult}</button></div>
      <p id="review-status" role="status" hidden></p><button id="review-retry" type="button" hidden>${ja.reviewRetry}</button>
      <div class="review-steps"><button id="review-first" type="button">${ja.reviewFirst}</button>
        <button id="review-prev" type="button">${ja.reviewPrev}</button><button id="review-next" type="button">${ja.reviewNext}</button>
        <button id="review-last" type="button">${ja.reviewLast}</button></div></div>`;
  layout.append(actions); shell.append(dialog);
  const get = <T extends HTMLElement>(id: string): T => shell.querySelector<T>(`#${id}`)!;
  return { dialog, actions, finished: get('finished-actions'), review: get('review-actions'),
    counter: get('review-counter'), status: get('review-status'), retry: get<HTMLButtonElement>('review-retry'),
    first: get<HTMLButtonElement>('review-first'), prev: get<HTMLButtonElement>('review-prev'),
    next: get<HTMLButtonElement>('review-next'), last: get<HTMLButtonElement>('review-last'),
    setResult(state: SessionState): void {
      const view = state.view; if (!view || view.winner === null) return;
      const player = view.winner === 0 ? ja.first : ja.second;
      get('result-heading').textContent = state.mode === 'ai'
        ? view.winner === state.humanSide ? ja.humanWon : ja.aiWon : `${player}${ja.winner}`;
      get('result-detail').textContent = `${player}${ja.reachedGoal}`;
      get('result-total').textContent = `${ja.totalMoves} ${view.ply}手`;
    } };
}
