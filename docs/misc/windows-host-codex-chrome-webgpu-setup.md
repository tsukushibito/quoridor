# Host Windows PC側 Codex 向け — DevContainer 連携 Chrome / WebGPU 環境構築手順

更新日: 2026-09-28

## 1. 目的

このドキュメントは、**Windows ホスト側で動作する Codex** が、DevContainer 内の Codex から制御可能な専用 Chrome を準備し、実 GPU を使った WebGPU / Three.js / VXGI 検証環境を構築するための作業指示書である。

最終構成:

```text
Windows Host
├─ Docker Desktop
│  └─ host networking
│
├─ Automation Chrome
│  ├─ dedicated user-data-dir
│  ├─ CDP: 127.0.0.1:9222
│  └─ WebGPU → Host GPU
│
└─ DevContainer
   └─ --network=host
      ├─ Codex
      ├─ Chrome DevTools MCP
      └─ 127.0.0.1:9222 → Host Chrome
```

目的は、DevContainer 内の Codex が Windows Chrome を操作しながら、**実 GPU 上の WebGPU/VXGI を含む動作確認を自律実行できること**である。

---

## 2. この Codex セッションの責務

Host Windows 側 Codex は以下を担当する。

1. Docker Desktop / Linux container mode の確認
2. host networking の有効化状況確認
3. Automation 専用 Chrome profile の準備
4. Remote Debugging Port 付き Chrome の起動方法整備
5. `127.0.0.1:9222` の疎通確認
6. host-network container から Chrome へ接続できることの確認
7. Host Chrome で WebGPU hardware acceleration が利用可能であることの確認
8. セキュリティ境界の維持

### スコープ外

以下は Host 側から勝手に変更しない。

- プロジェクトの Three.js 実装
- `.devcontainer/devcontainer.json`
- Container 内 Codex の `~/.codex/config.toml`
- プロジェクト固有の Vite / Playwright テスト

それらは DevContainer 側 Codex が担当する。

---

## 3. 前提

対象 OS:

```text
Windows 11
```

想定:

- Docker Desktop
- Linux containers
- Windows 上で hardware acceleration が有効な Chrome
- DevContainer を使用
- Remote Debugging Port: `9222`

---

## 4. Docker Desktop の確認

PowerShell で:

```powershell
docker version
docker info
docker desktop version
docker desktop status
```

確認事項:

- Docker Desktop が起動している
- Engine が Linux containers 側である
- Docker Desktop が少なくとも host networking 対応世代である

Docker の公式 Host network driver 文書では、Docker Desktop **4.34 以降**で host networking が opt-in 機能としてサポートされている。

### 4.1 Linux containers の確認

Windows container mode になっていないこと。

必要に応じて:

```powershell
docker desktop engine ls
```

利用可能なら Linux engine を選択する。

`docker info` の Server 側:

```text
OSType: linux
```

相当を確認する。

---

## 5. Docker Desktop host networking を有効化

Docker Desktop:

```text
Settings
→ Resources
→ Network
→ Enable host networking
→ Apply and restart
```

Docker 公式 Host network driver の説明では、この機能は双方向であり:

- host → container
- container → host

の TCP / UDP 通信を `localhost` 経由で可能にする。

### 重要: Windows の公式ドキュメント表記について

2026-09-28 時点で Docker 公式文書には表記の不整合がある。

- `Host network driver` ページ:
  - Docker Desktop 4.34+ をサポートと記載
  - 双方向通信を記載
- Docker Desktop `Settings` の Network 表:
  - `Enable host networking` の Platform 欄が `Mac` と表示されている

一方、Docker Desktop for Windows の実運用例・issue では 4.34+ の host networking が使用されている。

したがって Windows では**ドキュメントの表だけで判断せず、実機で以下を確認する**。

1. Docker Desktop UI に `Enable host networking` が存在する
2. 有効化できる
3. 実際の TCP smoke test が成功する

設定項目が表示されない、または smoke test が失敗する場合は、設定ファイルを非公式に直接編集して無理に有効化しないこと。

その場合は primary 構成を中止し、`host.docker.internal + secure CDP relay` 等の fallback を別途設計する。

---

## 6. Automation Chrome を通常 Chrome から分離する

### 6.1 原則

Codex に接続させる Chrome は、普段使いの Chrome profile と分離する。

理由:

Chrome DevTools Protocol に接続した agent は、接続先ブラウザのページ、cookie、ログイン状態等へアクセスできる。

**個人用 profile は絶対に使わない。**

### 6.2 Chrome 136+ の要件

Chrome 136 以降、デフォルトの Chrome data directory に対する:

```text
--remote-debugging-port
--remote-debugging-pipe
```

は制限されている。

Remote Debugging を使う場合は、非デフォルトの:

```text
--user-data-dir
```

を必ず指定する。

これは今回の用途でも必須要件とする。

---

## 7. Chrome 実行ファイルを検出する

PowerShell:

```powershell
$chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chrome = $chromeCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $chrome) {
    throw "Google Chrome executable was not found."
}

$chrome
```

Chrome for Testing を使用する場合は、その実行ファイル path を明示的に使う。

---

## 8. 推奨: Chrome for Testing

通常 Chrome + 専用 profile でもよいが、browser automation 専用環境としては Chrome for Testing も有力。

Chrome 公式も browser automation 用途には Chrome for Testing を推奨している。

利点:

- automation / testing 専用
- version pin が可能
- 通常 Chrome と分離しやすい
- auto-update による突然の再現性変化を抑えやすい

Node.js が Windows 側にある場合、公式ドキュメント例では:

```powershell
npx @puppeteer/browsers install chrome@stable
```

で取得できる。

ただし、このプロジェクトでは**使用 Chrome の path と version を記録し、勝手に頻繁に更新しないこと**。

---

## 9. Automation Chrome 起動スクリプト

プロジェクト運用上問題がなければ、Windows 側に次のようなスクリプトを作る。

推奨例:

```text
scripts/windows/start-codex-chrome.ps1
```

内容例:

```powershell
param(
    [int]$Port = 9222,
    [string]$ChromePath = ""
)

$ErrorActionPreference = "Stop"

if (-not $ChromePath) {
    if ($env:CODEX_CHROME_EXE -and (Test-Path $env:CODEX_CHROME_EXE)) {
        $ChromePath = $env:CODEX_CHROME_EXE
    } else {
        $candidates = @(
            "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        )

        $ChromePath = $candidates |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
    }
}

if (-not $ChromePath -or -not (Test-Path $ChromePath)) {
    throw "Chrome executable was not found. Set CODEX_CHROME_EXE or pass -ChromePath."
}

$profileDir = Join-Path $env:LOCALAPPDATA "CodexChromeProfile"

New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

$args = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$profileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
)

Write-Host "Launching: $ChromePath"
Write-Host "Profile:   $profileDir"
Write-Host "CDP:       http://127.0.0.1:$Port"

Start-Process `
    -FilePath $ChromePath `
    -ArgumentList $args
```

### 起動

```powershell
.\scripts\windows\start-codex-chrome.ps1
```

### 禁止する追加オプション

通常開発では以下を追加しない。

```text
--disable-gpu
--use-gl=swiftshader
--enable-unsafe-webgpu
--remote-debugging-address=0.0.0.0
```

目的は production に近い Windows Chrome + hardware WebGPU を検証することである。

---

## 10. Host Windows 上で CDP を確認

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

または:

```powershell
(Invoke-WebRequest http://127.0.0.1:9222/json/version).Content
```

期待:

```text
Browser
Protocol-Version
webSocketDebuggerUrl
```

が返る。

### Listener を確認

```powershell
Get-NetTCPConnection -LocalPort 9222 -State Listen |
    Format-Table LocalAddress, LocalPort, OwningProcess
```

Remote Debugging Port を LAN 全体へ意図せず公開しない。

`0.0.0.0:9222` や外部 NIC address に広く bind する構成は避ける。

---

## 11. Docker host networking の smoke test

Host Chrome が 9222 で起動した状態で、Windows PowerShell から:

```powershell
docker run --rm --network host curlimages/curl:latest `
    -fsS http://127.0.0.1:9222/json/version
```

成功すれば:

```json
{
  "Browser": "...",
  "Protocol-Version": "...",
  "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."
}
```

相当が返る。

これが**最重要の host-network smoke test**である。

### 成功した場合

DevContainer 側でも:

```text
--network=host
```

を使用すれば、同じ:

```text
http://127.0.0.1:9222
```

で Chrome へ到達できる可能性が高い。

### 失敗した場合

以下を順に確認する。

1. Docker Desktop 4.34+ か
2. Linux container mode か
3. Docker Desktop に sign-in しているか
4. `Enable host networking` が有効か
5. Apply / Restart 済みか
6. Chrome が本当に `127.0.0.1:9222` で待受しているか
7. VPN / endpoint security / firewall の影響
8. Docker Desktop の既知問題が出ていないか

host networking が利用不能な環境で、設定 store を直接書き換えて強行しない。

---

## 12. WebGPU hardware acceleration の確認

Automation Chrome で:

```text
chrome://gpu
```

を開く。

確認対象:

```text
WebGPU
```

が hardware acceleration を利用可能な状態であること。

単に JavaScript で:

```js
!!navigator.gpu
```

が `true` でも、期待する hardware path の保証としては不十分。

必要に応じて以下も確認する。

- Graphics Feature Status
- Problems Detected
- ANGLE / D3D backend
- GPU process
- Driver related warnings

### アプリ側確認

DevContainer の Vite が起動した後:

```text
http://127.0.0.1:5173
```

を Automation Chrome で開き、DevTools console または Codex 経由で:

```js
const adapter = await navigator.gpu?.requestAdapter();
console.log({
  hasNavigatorGpu: !!navigator.gpu,
  hasAdapter: !!adapter
});
```

が成功することを確認する。

---

## 13. Three.js / VXGI に関する Host 側の合格条件

Three.js の `WebGPURenderer` は WebGPU が使えない場合 WebGL2 backend へ fallback できる。

しかし Three.js `VXGINode` は:

```text
WebGPURenderer + WebGPU backend
```

専用。

したがって Host 側では少なくとも:

- WebGPU hardware acceleration が使える
- `navigator.gpu.requestAdapter()` が成功
- アプリが Host Chrome 上で正常描画
- Console に WebGPU device / shader error がない

ことを保証する。

アプリ内部の `rendererBackend` / `vxgiEnabled` の判定は DevContainer 側 Codex の責務とする。

---

## 14. Remote Debugging のセキュリティルール

Remote Debugging Port は高権限なデバッグ経路である。

厳守:

- Automation 専用 profile のみ使用
- 個人用 Chrome profile は使用禁止
- Gmail / GitHub / SNS / 金融サービス等へログインしない
- パスワードを保存しない
- CDP 9222 を LAN / WAN へ公開しない
- Router port forwarding 禁止
- `--remote-debugging-address=0.0.0.0` を使わない
- Remote Debugging 中の browser は信頼できるローカル開発コンテンツに限定
- 作業終了後は Automation Chrome を終了してよい

Chrome DevTools MCP 公式も、agent が接続ブラウザのコンテンツを読み取り・操作できる点を明示している。

---

## 15. Windows 起動時の常駐について

最初の環境構築では Automation Chrome の自動起動を設定しない。

理由:

- Remote Debugging Port を常時開く必要がない
- Chrome version update 時の問題を発見しやすい
- 開発時だけ明示的に起動した方が安全

開発フローが安定した後に必要なら:

```text
Task Scheduler
```

等を検討する。

その場合も専用 profile と loopback CDP の原則を維持する。

---

## 16. トラブルシュート

### `Invoke-RestMethod 127.0.0.1:9222` が失敗

Chrome process を確認:

```powershell
Get-Process chrome -ErrorAction SilentlyContinue
```

port:

```powershell
Get-NetTCPConnection -LocalPort 9222 -ErrorAction SilentlyContinue
```

Chrome 136+ では専用 `--user-data-dir` が必須。

既存の通常 Chrome process が引数を吸収してしまう場合があるため、Automation Chrome は専用 profile で明示的に別 instance として起動する。

### Host では CDP が見えるが Docker smoke test が失敗

Docker Desktop host networking の問題として切り分ける。

```powershell
docker desktop status
docker info
```

Docker Desktop UI の host networking を再確認。

必要なら Docker Desktop を:

```powershell
docker desktop restart
```

して再試験する。

### `chrome://gpu` で WebGPU が software / unavailable

確認:

- Chrome hardware acceleration
- GPU driver
- Windows graphics settings
- Remote Desktop / VM 等の実行環境
- Chrome flags の異常設定
- `--disable-gpu` が付いていないか

通常開発では `--enable-unsafe-webgpu` に頼って合格扱いしない。

### Vite が Host Chrome から見えない

DevContainer 側が:

```bash
pnpm dev --host 0.0.0.0
```

で起動しているか確認する。

DevContainer 自体が:

```text
--network=host
```

で rebuild されている必要がある。

---

## 17. host networking を使えない場合

Primary 構成は:

```text
Docker Desktop host networking
+
Chrome 127.0.0.1:9222
```

とする。

host networking が Windows 実機で利用できない場合、**その場で CDP を外部 NIC に公開して解決しないこと**。

Fallback は別設計とする。

候補:

```text
bridge network
+ host.docker.internal
+ loopback CDP
+ Windows 側 secure TCP relay
+ firewall scope 制限
+ chrome-devtools-mcp --ws-endpoint
```

これは:

- CDP WebSocket URL の書き換え
- relay の bind address
- Windows Firewall scope
- Chrome 再起動ごとに変わる browser WebSocket endpoint

を扱う必要があり、primary 構成より複雑である。

host networking が使えないことを確認した時点で、別タスクとして設計・実装する。

---

## 18. 完了条件

Host Windows 側の構築は以下をすべて満たしたら完了。

- [ ] Docker Desktop が起動している
- [ ] Linux containers を使用している
- [ ] Docker Desktop host networking が有効
- [ ] Automation Chrome が専用 profile で起動する
- [ ] CDP が `127.0.0.1:9222` で利用可能
- [ ] Host の `Invoke-RestMethod` で `/json/version` を取得できる
- [ ] `docker run --network host` から `/json/version` を取得できる
- [ ] Automation Chrome で WebGPU hardware acceleration を確認できる
- [ ] Automation Chrome に個人アカウントを入れていない
- [ ] CDP port を LAN / WAN へ公開していない
- [ ] DevContainer 側へ `http://127.0.0.1:9222` を接続先として引き渡せる

---

## 19. DevContainer 側 Codex へ渡す情報

Host 作業完了後、DevContainer 側へ次だけ伝える。

```text
Chrome CDP URL:
http://127.0.0.1:9222

App URL:
http://127.0.0.1:5173

Networking:
DevContainer must run with --network=host.
```

secret / token は不要。

---

## 20. 参考資料

- Docker — Host network driver  
  https://docs.docker.com/engine/network/drivers/host/

- Docker — Docker Desktop settings  
  https://docs.docker.com/desktop/settings-and-maintenance/settings/

- Docker — Networking on Docker Desktop  
  https://docs.docker.com/desktop/features/networking/

- Docker — Docker Desktop CLI  
  https://docs.docker.com/desktop/features/desktop-cli/

- Chrome — Changes to remote debugging switches (Chrome 136+)  
  https://developer.chrome.com/blog/remote-debugging-port

- Chrome — Chrome DevTools for agents / Configuration  
  https://developer.chrome.com/docs/devtools/agents/get-started/configuration

- Chrome — Chrome for Testing  
  https://developer.chrome.com/docs/automation-and-testing/chrome-for-testing

- Chrome — Download Chrome for Testing binaries  
  https://developer.chrome.com/docs/automation-and-testing/download-test-binaries

- Three.js — WebGPURenderer  
  https://threejs.org/docs/pages/WebGPURenderer.html

- Three.js — VXGINode  
  https://threejs.org/docs/pages/VXGINode.html
