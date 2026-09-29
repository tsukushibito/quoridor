# DevContainer側 Codex 向け — Host Windows Chrome / WebGPU 開発環境構築手順

更新日: 2026-09-28

## 1. 目的

このドキュメントは、**DevContainer 内で動作する Codex** が、Windows ホスト上で動作する Chrome を Chrome DevTools Protocol (CDP) 経由で制御し、以下を自律的に行える開発環境を構築するための作業指示書である。

- TypeScript / Vite / Three.js の実装
- Three.js `WebGPURenderer` の実ブラウザ動作確認
- WebGPU バックエンド上の VXGI 動作確認
- Console / Network / Performance の確認
- ブラウザ操作
- スクリーンショット取得と視覚確認
- 必要に応じた Playwright E2E
- 実装 → 実行 → 確認 → 修正の反復

最終構成:

```text
Windows Host
├─ Chrome / Chrome for Testing
│  ├─ CDP: 127.0.0.1:9222
│  └─ WebGPU → Host GPU
│
└─ Docker Desktop host networking
             ↕ localhost
DevContainer
├─ Codex CLI
├─ Node.js / pnpm / Vite / TypeScript
├─ Three.js
├─ Chrome DevTools MCP
└─ Playwright（必要に応じて）
```

**重要:** WebGPU のレンダリングは DevContainer 内ではなく、Windows ホスト側 Chrome とホスト GPU で実行する。

---

## 2. この Codex セッションの責務

この DevContainer 側 Codex は以下を担当する。

1. DevContainer を host network で起動する設定
2. Container → Host Chrome の CDP 疎通確認
3. Chrome DevTools MCP の Codex 設定
4. Vite 開発サーバーの起動設定
5. WebGPU / Three.js / VXGI の動作確認用基盤
6. 必要なら Playwright から Host Chrome へ接続する基盤
7. 再現可能な検証コマンドの整備

### スコープ外

以下はこのセッションでは変更しない。

- Windows の Docker Desktop GUI 設定
- Windows Chrome のインストール
- Windows Chrome の起動スクリプト
- GPU ドライバ設定
- Windows Defender Firewall の恒久設定

これらは Host Windows 側の作業指示書で行う。

---

## 3. 前提条件

Host Windows 側の作業が完了しており、少なくとも次を満たしていること。

- Docker Desktop が起動済み
- Linux containers を使用中
- Docker Desktop の host networking が有効
- Windows 側 Chrome が次の条件で起動済み
  - Remote Debugging Port: `9222`
  - 専用 `--user-data-dir`
  - 通常ユーザーの Chrome プロファイルとは分離
- Host Windows 上で以下が成功する

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

Host 側が未完了なら、このドキュメントの作業を途中で無理に迂回せず、Host Windows 側指示書を先に完了させること。

---

## 4. DevContainer を host network で起動する

### 4.1 `devcontainer.json` を使う場合

既存の `.devcontainer/devcontainer.json` に `runArgs` を追加する。

例:

```jsonc
{
  "name": "quoridor-web",

  // 既存設定は維持すること。
  "runArgs": [
    "--network=host"
  ]
}
```

既に `runArgs` がある場合は**上書きせず**、配列へ `--network=host` を追加する。

`forwardPorts` は host network では必須ではない。既存設定が他用途で使われている場合は削除しなくてよいが、Docker の `-p` / publish 相当は host network では意味を持たない点に注意する。

### 4.2 Docker Compose ベースの場合

対象 service に以下を追加する。

```yaml
services:
  dev:
    network_mode: host
```

`ports:` による Docker port publish と `network_mode: host` の併用に依存しないこと。

### 4.3 Rebuild

設定変更後は、単なる VS Code 再接続ではなく DevContainer を rebuild する。

VS Code:

```text
Dev Containers: Rebuild Container
```

再構築後、Container 内で確認する。

```bash
ip addr
```

host network の実装は Docker Desktop 上では Linux native host network と完全に同一ではないため、インターフェース構成だけを合否判定に使わない。**実際の TCP 疎通を合否判定に使うこと。**

---

## 5. Host Chrome への CDP 疎通確認

Container 内で実行:

```bash
curl --fail --show-error --silent \
  http://127.0.0.1:9222/json/version
```

期待する結果の例:

```json
{
  "Browser": "Chrome/...",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."
}
```

最低限、次を確認する。

```bash
curl -fsS http://127.0.0.1:9222/json/version \
  | python -m json.tool
```

### 合格条件

- HTTP 200 相当で JSON を取得できる
- `Browser`
- `Protocol-Version`
- `webSocketDebuggerUrl`

が存在する。

### 失敗した場合

順番に確認する。

```bash
# 1. host network で起動しているか
cat /proc/1/cgroup || true

# 2. 9222 の疎通
curl -v http://127.0.0.1:9222/json/version
```

そのうえで Host 側 Codex に以下を確認させる。

- Chrome がまだ起動しているか
- `127.0.0.1:9222` で待受しているか
- Docker Desktop の host networking が実際に有効か
- DevContainer を設定変更後に rebuild したか

**`host.docker.internal` へ安易に切り替えないこと。**  
CDP の `/json/version` が返す WebSocket URL が `127.0.0.1` を含むため、bridge network へ戻すと WebSocket 接続経路の追加処理が必要になる。

---

## 6. Codex に Chrome DevTools MCP を設定する

### 6.1 前提確認

Container 内で:

```bash
node --version
npm --version
npx --version
codex --version
```

`npx` が使えること。

### 6.2 `~/.codex/config.toml`

ユーザーレベルの Codex 設定へ次を追加する。

```toml
[mcp_servers.chrome_devtools]
command = "npx"
args = [
  "-y",
  "chrome-devtools-mcp@latest",
  "--browser-url=http://127.0.0.1:9222"
]
```

既存 `config.toml` の内容を破壊しないこと。

可能なら編集前にバックアップする。

```bash
cp ~/.codex/config.toml ~/.codex/config.toml.bak.$(date +%Y%m%d%H%M%S)
```

ファイルが存在しない場合のみ新規作成する。

### 6.3 Codex から確認

```bash
codex mcp list
```

`chrome_devtools` または設定したサーバー名が表示されること。

Codex セッションが既に起動中だった場合は、MCP 設定を再読込させるため Codex セッションを再起動する。

### 6.4 MCP 動作テスト

Codex に以下と同等の確認を実施させる。

```text
Chrome DevTools MCP を使用して、新しいタブで about:blank を開き、
ページ一覧を取得し、スクリーンショットを1枚取得してください。
```

次に Vite 起動後、

```text
http://127.0.0.1:5173
```

を開かせる。

MCP で最低限確認すべき機能:

- page navigation
- console message inspection
- network inspection
- screenshot
- DOM snapshot
- performance trace

---

## 7. Vite 開発サーバー

### 7.1 推奨起動方法

Vite は Container 側で起動する。

```bash
pnpm dev --host 0.0.0.0
```

または `package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0"
  }
}
```

Host Chrome から:

```text
http://127.0.0.1:5173
```

へアクセスする。

### 7.2 ポート競合

host network では Host と Container の TCP ポート競合を意識する。

Container 側:

```bash
ss -ltnp | grep ':5173' || true
```

Host 側で既に `5173` が使用中なら別ポートを採用する。

例:

```bash
pnpm dev --host 0.0.0.0 --port 5174
```

ポートを変更した場合は MCP / Playwright 側の対象 URL も更新する。

---

## 8. WebGPU のスモークテスト

アプリ側で最低限、以下を確認できるようにする。

```ts
export async function probeWebGpu() {
  const hasNavigatorGpu = typeof navigator !== "undefined" && !!navigator.gpu;

  if (!hasNavigatorGpu) {
    return {
      hasNavigatorGpu: false,
      hasAdapter: false,
    };
  }

  const adapter = await navigator.gpu.requestAdapter();

  return {
    hasNavigatorGpu: true,
    hasAdapter: adapter !== null,
  };
}
```

Chrome DevTools MCP からページ上で評価し、

```text
hasNavigatorGpu = true
hasAdapter = true
```

となることを確認する。

**このテストだけでは hardware acceleration の保証にはならない。**  
Host Windows 側で `chrome://gpu` を確認し、WebGPU が hardware accelerated であることを別途確認する。

---

## 9. Three.js WebGPURenderer / VXGI の検証方針

Three.js の `WebGPURenderer` は WebGPU 非対応環境では WebGL2 backend へ fallback できる。一方、`VXGINode` は **WebGPURenderer + WebGPU backend 専用**である。

したがって単に「画面が描画できた」だけでは VXGI の検証にならない。

開発中はアプリに明示的な診断情報を持たせることを推奨する。

例:

```ts
declare global {
  interface Window {
    __QUORIDOR_DIAGNOSTICS__?: {
      webgpuAvailable: boolean;
      webgpuAdapterAvailable: boolean;
      rendererBackend: "webgpu" | "webgl2" | "unknown";
      vxgiEnabled: boolean;
      buildId?: string;
    };
  }
}
```

開発ビルドで:

```ts
window.__QUORIDOR_DIAGNOSTICS__ = {
  webgpuAvailable: !!navigator.gpu,
  webgpuAdapterAvailable: false,
  rendererBackend: "unknown",
  vxgiEnabled: false,
};
```

実際の初期化結果に応じて値を更新する。

Codex は画面だけでなくこの診断値を読み、少なくとも以下を確認する。

```text
webgpuAvailable = true
webgpuAdapterAvailable = true
rendererBackend = webgpu
vxgiEnabled = true
```

**WebGL2 fallback 中に VXGI テストを合格扱いしてはならない。**

---

## 10. Playwright から Host Chrome へ接続する場合

Chrome DevTools MCP だけで十分な操作は MCP を優先する。

再現可能な E2E や assertion が必要な場合は Playwright を併用する。

### 10.1 インストール

```bash
pnpm add -D @playwright/test
```

Host Chrome に CDP 接続するだけなら、Container 内ブラウザをメイン検証対象にする必要はない。

### 10.2 最小 CDP スモークテスト

例: `scripts/smoke-host-chrome.mts`

```ts
import { chromium } from "@playwright/test";

const endpoint = process.env.CHROME_CDP_URL ?? "http://127.0.0.1:9222";
const appUrl = process.env.APP_URL ?? "http://127.0.0.1:5173";

const browser = await chromium.connectOverCDP(endpoint, {
  // Browser は Windows、Playwright は Container。
  // localhost で接続できてもファイルシステムは同一ではない。
  isLocal: false,
});

const context = browser.contexts()[0];
if (!context) {
  throw new Error("Chrome default browser context was not found.");
}

const page = await context.newPage();

try {
  await page.goto(appUrl, { waitUntil: "networkidle" });

  const gpu = await page.evaluate(async () => {
    if (!navigator.gpu) {
      return { hasNavigatorGpu: false, hasAdapter: false };
    }

    const adapter = await navigator.gpu.requestAdapter();

    return {
      hasNavigatorGpu: true,
      hasAdapter: adapter !== null,
    };
  });

  console.log("WebGPU probe:", gpu);

  if (!gpu.hasNavigatorGpu || !gpu.hasAdapter) {
    throw new Error("WebGPU adapter is unavailable in host Chrome.");
  }

  await page.screenshot({
    path: "artifacts/host-webgpu-smoke.png",
    fullPage: true,
  });
} finally {
  await page.close();

  // connectOverCDP の Browser は remote browser 接続。
  // 使用中の Playwright バージョンで browser.close() が
  // 意図した「接続終了」の挙動になることを確認してから使用する。
}
```

まずはスクリプトを一度だけ実行して挙動を確認する。

```bash
mkdir -p artifacts
node --import tsx scripts/smoke-host-chrome.mts
```

`tsx` を使うなら:

```bash
pnpm add -D tsx
```

### 10.3 Playwright の注意

`connectOverCDP()` は Chromium 系ブラウザ限定で、Playwright 自身も通常の Playwright protocol 接続より低 fidelity としている。

この構成では目的を以下に限定する。

- 実 Chrome / 実 WebGPU の確認
- 画面操作
- screenshot
- console / page assertion
- 軽量な E2E

Playwright 固有の高度機能に問題が出た場合は、Chrome DevTools MCP / CDP での検証へ切り分ける。

---

## 11. Codex に要求する通常の検証ループ

WebGPU / graphics に関係しない変更:

```text
実装
↓
pnpm lint
↓
pnpm typecheck
↓
pnpm test
↓
必要なら通常 E2E
```

レンダリングに関係する変更:

```text
実装
↓
lint / typecheck / unit test
↓
Vite 起動
↓
Chrome DevTools MCP で Host Chrome を操作
↓
console error 確認
↓
WebGPU 診断値確認
↓
VXGI 有効状態確認
↓
screenshot
↓
必要なら performance trace
↓
修正
```

以下を変更した場合は Host Chrome の実 GPU 確認を必須とする。

- `WebGPURenderer`
- TSL
- `VXGINode`
- Light / Shadow
- Render target
- Post processing
- PBR material
- HDR / environment
- GPU resource lifetime
- WebGPU feature / limit 依存コード

---

## 12. Codex 用 `AGENTS.md` への推奨追記

プロジェクトの方針と矛盾しない場合、以下と同等のルールを追加する。

```md
## Browser / WebGPU verification

- The application uses a Windows-host Chrome instance for authoritative WebGPU
  and graphics verification.
- Chrome DevTools MCP connects to `http://127.0.0.1:9222`.
- Before claiming a WebGPU/VXGI task complete, verify the change in the
  host Chrome, not only with static checks or a container-local browser.
- Confirm that the renderer is actually using the WebGPU backend when testing
  VXGI. A successful WebGL2 fallback is not sufficient.
- Inspect console errors and capture a screenshot for graphics-affecting changes.
- Do not alter Windows host configuration from inside the DevContainer.
- Do not use or log into personal accounts in the automation Chrome profile.
```

既存 `AGENTS.md` の指示を尊重し、重複・矛盾を避ける。

---

## 13. セキュリティ要件

Chrome の Remote Debugging Port は、接続者にブラウザをほぼ全面的に制御する能力を与える。

必ず以下を守る。

- 専用 Chrome profile を使う
- 普段使いの Chrome profile を接続しない
- 個人 Gmail、GitHub、銀行、SNS 等へログインしない
- Remote Debugging Port を LAN へ公開しない
- `--remote-debugging-address=0.0.0.0` を追加しない
- CDP ポートをインターネットへ port forward しない
- スクリーンショット・trace・console log に secret を残さない
- 認証情報をリポジトリへ commit しない

---

## 14. トラブルシュート

### `curl 127.0.0.1:9222` が Connection refused

主な原因:

1. Host Chrome が起動していない
2. Chrome が 9222 以外で起動している
3. Docker Desktop host networking が無効
4. DevContainer が `--network=host` なしで起動中
5. DevContainer rebuild 前の古い container を使っている

### `/json/version` は取れるが MCP が接続できない

確認:

```bash
npx -y chrome-devtools-mcp@latest --help
```

次に:

```bash
codex mcp list
```

`config.toml` の `--browser-url` を確認する。

```text
http://127.0.0.1:9222
```

`--autoConnect` はこの構成の第一選択にしない。  
MCP プロセスは Container 内にいるため、Host Windows Chrome へは明示的な URL 接続の方が構成が明確である。

### Host Chrome から Vite に接続できない

Container:

```bash
ss -ltnp | grep ':5173'
```

Vite は:

```bash
pnpm dev --host 0.0.0.0
```

で起動する。

### `navigator.gpu` が無い

Host 側を確認する。

- 対象が本当に Windows Host Chrome か
- Chrome が十分新しいか
- GPU acceleration が無効化されていないか
- `chrome://gpu` の WebGPU 状態
- RDP / VM / driver 等で GPU が無効化されていないか

### Three.js は描画できるが VXGI が使えない

`WebGPURenderer` が WebGL2 backend へ fallback していないか確認する。

VXGI は WebGPU backend 必須。

---

## 15. 完了条件

この DevContainer 側環境構築は、以下をすべて満たしたら完了とする。

- [ ] DevContainer が host network で起動する
- [ ] Container から `http://127.0.0.1:9222/json/version` を取得できる
- [ ] `codex mcp list` で Chrome DevTools MCP を確認できる
- [ ] Codex から Host Chrome のタブを操作できる
- [ ] Codex から screenshot を取得できる
- [ ] Container の Vite を Host Chrome から開ける
- [ ] `navigator.gpu` が存在する
- [ ] `navigator.gpu.requestAdapter()` が成功する
- [ ] Three.js が WebGPU backend で動作していることをアプリ側から確認できる
- [ ] VXGI 有効時に WebGL2 fallback を誤って合格扱いしない
- [ ] graphics 変更に対する Codex の検証ループが定義されている

---

## 16. 参考資料

- Docker — Host network driver  
  https://docs.docker.com/engine/network/drivers/host/

- Docker — Networking on Docker Desktop  
  https://docs.docker.com/desktop/features/networking/

- Chrome DevTools for agents — Configuration  
  https://developer.chrome.com/docs/devtools/agents/get-started/configuration

- Chrome DevTools MCP — configuration  
  https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/configuration.md

- OpenAI — Codex / MCP  
  https://developers.openai.com/learn/docs-mcp

- Playwright — `browserType.connectOverCDP()`  
  https://playwright.dev/docs/api/class-browsertype

- Three.js — `WebGPURenderer`  
  https://threejs.org/docs/pages/WebGPURenderer.html

- Three.js — `VXGINode`  
  https://threejs.org/docs/pages/VXGINode.html
