const board = (label: string, pieces: string, arrows = '', wall = ''): string => {
  const tiles = Array.from({ length: 25 }, (_, id) => `<rect x="${10 + id % 5 * 32}" y="${10 + Math.floor(id / 5) * 32}" width="29" height="29" rx="3"/>`).join('');
  return `<svg viewBox="0 0 180 180" role="img" aria-label="${label}"><g fill="#655246" stroke="#9e8067" stroke-width="1">${tiles}</g>${wall}<g stroke="#80dbc6" stroke-width="4" fill="none">${arrows}</g>${pieces}</svg>`;
};
const pawn = (col: number, row: number, color: string, hex = false): string => {
  const x = 24.5 + col * 32, y = 24.5 + row * 32;
  const shape = hex ? `polygon points="${Array.from({ length: 6 }, (_, i) => `${x + 11 * Math.cos(i * Math.PI / 3)},${y + 11 * Math.sin(i * Math.PI / 3)}`).join(' ')}"` : `circle cx="${x}" cy="${y}" r="10"`;
  return `<${shape} fill="${color}" stroke="#f6e2bd" stroke-width="2"/>`;
};
const diagrams = [
  board('自分の駒を反対側の端へ進める', pawn(2, 4, '#42abc3'), '<path d="M88.5 138V34m-8 10 8-10 8 10"/>', '<rect x="10" y="10" width="157" height="29" rx="3" fill="#d7ac73" opacity=".55"/>'),
  board('向かい合う駒を直線で飛び越す', pawn(2, 3, '#42abc3') + pawn(2, 2, '#e5906d', true), '<path d="M105 118V56m-8 10 8-10 8 10"/>'),
  board('相手の後ろが壁なら横へ回り込む', pawn(2, 3, '#42abc3') + pawn(2, 2, '#e5906d', true), '<path d="M88 110 56 88m3 10-3-10 10 1M89 110 121 88m-10 1 10-1-3 10"/>', '<rect x="73" y="71" width="61" height="5" rx="2" fill="#f2d7ac"/>'),
  board('壁は2マス分を遮り、ゴールへの道を残す', pawn(2, 4, '#42abc3'), '<path d="M88 140 88 119 56 119 56 55m-8 10 8-10 8 10"/>', '<rect x="73" y="103" width="61" height="5" rx="2" fill="#f2d7ac"/>'),
];

export function createTitleHelp(shell: HTMLElement, menu: HTMLDialogElement, actions: HTMLElement, logoUrl: string) {
  const title = document.createElement('section');
  title.id = 'startup-dialog'; title.className = 'title-screen'; title.setAttribute('aria-labelledby', 'title-heading');
  title.innerHTML = `<div class="title-content"><h1 id="title-heading" class="title-logo" style="--logo-url:url('${logoUrl}')"><img src="${logoUrl}" alt="QUORIDOR" width="2020" height="778"><span class="logo-fallback" hidden>QUORIDOR</span></h1>
    <p class="title-subtitle">一歩進むか、道を変えるか。</p>
    <nav class="title-menu" aria-label="開始メニュー"><button id="resume-game-choice" class="accent" type="button" hidden>続きから遊ぶ</button><button id="startup-new-game" type="button">新しく遊ぶ</button><button id="title-help" type="button">遊び方</button></nav>
    <p id="startup-message" class="title-message" role="status"></p><button id="startup-clear-save" class="title-clear" type="button" hidden>保存を消す</button></div>`;
  const img = title.querySelector<HTMLImageElement>('img')!;
  img.addEventListener('error', () => { img.hidden = true; title.querySelector<HTMLElement>('.logo-fallback')!.hidden = false; title.querySelector('.title-logo')!.classList.add('logo-missing'); });
  const help = document.createElement('dialog'); help.id = 'help-dialog'; help.className = 'app-dialog help-dialog';
  help.setAttribute('aria-labelledby', 'help-heading');
  help.innerHTML = `<div class="dialog-head"><h2 id="help-heading">遊び方</h2><button id="close-help" type="button">閉じる</button></div>
    <p class="help-intro">向こう岸を目指す、2人の道づくり。<span>対局中は、この説明を閉じるまで進行が止まります。</span></p>
    <section class="help-section"><div><h3>1. 反対側の端へ、先に到着する</h3><p>自分の駒を、出発した側と反対の端のどこかへ到達させた人が勝ちです。先手は丸い青緑の駒、後手は六角の赤い駒です。</p></div><figure>${diagrams[0]}<figcaption>反対側の端がゴール</figcaption></figure></section>
    <section class="help-section"><div><h3>2. 駒を動かす、または壁を置く</h3><p>交互に1手ずつ。自分の手番では、駒を上下左右へ1マス動かすか、壁を1枚置きます。各自の壁は10枚。壁は2マス分の間を遮り、置いた後は動かせません。</p><p>壁を重ねたり交差させたり、どちらかの駒のゴールへの道をすべて塞いだりする配置はできません。</p></div><figure>${diagrams[3]}<figcaption>遠回りでも、道は残す</figcaption></figure></section>
    <section class="help-section"><div><h3>3. 相手の駒は飛び越せる</h3><p>隣に相手の駒があり、その後ろへ進めるときは、相手を直線で飛び越せます。相手の後ろが壁や盤の端なら、通れる横側へ斜めに回り込めます。</p><p>壁を飛び越えることはできません。実際に動けるマスは盤上で光ります。</p></div><div class="help-figures"><figure>${diagrams[1]}<figcaption>直線で飛び越す</figcaption></figure><figure>${diagrams[2]}<figcaption>後ろが塞がれたとき</figcaption></figure></div></section>
    <section class="help-section help-controls"><div><h3>4. PCでの操作</h3><dl><dt>駒を動かす</dt><dd>「駒を動かす」を選び、光る移動先をクリック。</dd><dt>壁を置く</dt><dd>「壁を置く」を選び、位置にマウスを合わせてプレビュー。クリックで確定。「壁の向き」またはRキーで向きを変更。</dd><dt>キーボード</dt><dd>盤にフォーカスし、矢印キーで候補、Enterで確定、Escapeで解除。</dd><dt>視点</dt><dd>右ドラッグで回転、ホイールで拡大縮小。「設定・保存」で視点を戻せます。</dd><dt>取り消しと保存</dt><dd>「1手戻す」で取り消し。AI対戦では直前の自分の判断まで戻ります。着手ごとに、このブラウザへ1対局分を自動保存します。</dd></dl></div></section>
    <div class="dialog-actions"><button id="close-help-bottom" class="accent" type="button">閉じて戻る</button></div>`;
  const restart = document.createElement('dialog'); restart.id = 'restart-dialog'; restart.className = 'app-dialog';
  restart.setAttribute('aria-labelledby', 'restart-heading');
  restart.innerHTML = `<h2 id="restart-heading">最初からやり直しますか？</h2><p>今の対局と保存した進行は、最初の状態に置き換わります。対戦条件は同じです。</p><div class="dialog-actions"><button id="restart-cancel" type="button">キャンセル</button><button id="restart-confirm" class="accent" type="button">やり直す</button></div>`;
  const helpButton = document.createElement('button'); helpButton.id = 'open-help'; helpButton.type = 'button'; helpButton.textContent = '？ 遊び方';
  actions.insertBefore(helpButton, actions.lastElementChild);
  const returnTitle = document.createElement('button'); returnTitle.id = 'return-title'; returnTitle.type = 'button'; returnTitle.textContent = 'タイトルへ戻る';
  const row = document.createElement('div'); row.className = 'dialog-actions'; row.append(returnTitle); menu.append(row);
  shell.append(title, help, restart);
  return { title, help, restart, returnTitle, helpButton };
}
