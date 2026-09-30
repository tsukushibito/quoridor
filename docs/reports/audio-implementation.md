# SE・BGMとサウンド設定の実装・検証

実施日: 2026-09-30。Beads: `quoridor-xyg`。
作業場所: `/workspaces/quoridor/.worktree/webapp-audio`、ブランチ `codex/webapp-audio`、開始点 `2b24675`。
設計は [11.6 サウンド](../design/quoridor-3d-webapp-design-rust-wasm-v1.md#116-サウンド2026-09-30追加)、音源の出典とハッシュは [manifest](../../apps/web/public/assets/audio/manifest.json) を参照する。
並行worktreeとmainのソースは変更していない。commit・push・mainへの統合は行っていない。

## 実装

- Kenneyの木の打音を駒/壁、短い操作音をメニュー/待った/終局に採用。Indieteur「Mystical Piano」を作者指定の95秒ループで再生。全てCC0、ローカル配信。
- 初期設定はSE/BGMともON、SE 55%、BGM 20%。上部のワンタップ消音、設定先頭の独立ON/OFF・0〜100%音量・SE試聴・クレジットを実装。native checkbox/range、数値、aria-pressed/aria-valuetext、44pxの新設操作領域を使用する。
- 設定は独立キー `quoridor.audio.settings.v1` に保存。既存のゲーム/表示設定の形式を変えず、保存できなくても現在のタブで有効。消音・個別OFFは音量を保持し、音量操作で勝手にONにしない。
- 1つのAudioContextと独立GainNodeを所有し、25msの音量補間、消音時のBGMフェード、6音までのSE同時再生を実装。着手音は有効なアニメーション完了、待ったは成功時、終局音は最後の着手音の後。過去のSEを待ち行列に溜めない。
- trustedクリック/タップ/キー操作で開始・再開。対局開始を音源取得で待たせず、取得/デコード/resumeを8秒で打ち切る。失敗表示と再試行を用意。背景では音源を止め、BGM位置だけを保持する。新規対局・保存復帰・描画復旧ではBGMを重複起動しない。

## 音源確認

採用ファイルは合計 **1,613,150 bytes**、BGMは **1,520,996 bytes**。6ファイルのSHA-256とmanifestが一致。PCMに戻したBGMは95.0秒、ピーク0.6847（フルスケール未満）、RMS 0.0881。95秒末尾と開始のサンプル差は0.00116。短い境界フェードを適用したうえで、Web AudioのloopEnd=95を使用する。

SEは44.1kHz mono PCM16 WAV。平均レベルは駒 -24.2dBFS、壁 -24.5dBFS、クリック -28.2dBFS、待った -23.3dBFS、終局 約-21.5dBFS。密度の高い終局音には追加の-8dBを適用した。素材ページのcalm/ambient表記と木製盤の設計を選定根拠にし、カフェの雑踏や歌声は追加していない。

数値根拠: `artifacts/audio-asset-verification.json`。これらは音の非無音・クリッピング・ループ境界の数値確認であり、人間の耳による聴感評価ではない。

## 検証

| 検証 | 結果 |
| --- | --- |
| `npm run typecheck` | 成功 |
| `npm run build`（release Wasmと通常production） | 成功。既存の大きいJS chunkの注意表示あり |
| `npm run test:audio` | 設定・独立保存・破損/サイズ/保存エラーの3件成功 |
| `npm run test:render` | 既存6件成功 |
| `node scripts/check-boundaries.mjs` | 成功 |
| Chromium production root | 音声10件成功。設定復元・人間/AI・壁・終局・取消・失敗復旧・タブ復帰・タッチ/キーボード・実信号/消音を確認 |
| WebKit development | 音声9件と実信号/消音1件成功 |
| Firefox development（Xvfb/PulseAudio） | 音声10件成功 |
| Firefox音声出力未提供 | resumeが8秒でblockedになり、音なしで1手進行。`artifacts/audio-device-timeout.json` |
| 既存HUD/対局/AI/保存/描画復旧 | 34ケースを実行。時計を停止する長いケース以外の33件は初回または再確認で成功 |

production rootとsubpathの音声検証には `VITE_PHASE1_E2E=1` で観測口を有効化したビルドを使う。通常productionでは観測口を除く。スクリーンショットは `artifacts/audio-320.png`、`audio-390.png`、`audio-1280.png` に保存する。

初回の既存+音声43件では39件成功、4件が時間切れ。描画復旧と保存破損出口は再確認で成功、AI両側の保存復帰はproductionで90秒上限を指定して36.1秒で成功した。長い `drag and UI isolation...` はfake clockで描画時間を操作し、SwiftShader上で90秒上限に達する。短い中断・待った・再作成・disposeの音声検証は成功している。この長いケースの結果を音声テスト成功と混同しない。

変更前の `2b24675` のmain/style/strings/test APIをGitから読み取り、Viteのloadで返す診断server（5188、専用cache）でも同じ時計停止ケースを実行した。アプリへの音声導入なしでも、最終dispose後の `page.clock.resume()` → `waitForTimeout(260)` で90秒上限に達した。根拠は `artifacts/audio-before-baseline/`。基準コードはリポジトリへ書き戻していない。

## 再現方法と環境

専用worktreeで `npm ci`、`npm run wasm:build:dev`。ブラウザは `artifacts/playwright` に配置する。`npm run test:audio:browsers` でChromium/Firefox/WebKitを指定できる。

```bash
VITE_PHASE1_E2E=1 npm run dev -w @quoridor/web -- --port 5186
E2E_BASE_URL=http://127.0.0.1:5186/ npm run test:audio:browsers -- --project chromium --project webkit
```

FirefoxはこのコンテナのヘッドレスGLで `FEATURE_FAILURE_WEBGL_EXHAUSTED_DRIVERS` が出るため、Xvfbを使用する。共有 `~/.cache` の権限によるprofile起動失敗は、音声テストconfigのworktree内cacheで回避する。音声出力装置のない環境にはPulseAudioのnull sinkを使用した。これは人間に音を届ける実機検証ではなく、ブラウザの音声グラフを動作させる検証環境である。

```bash
mkdir -p artifacts/audio-pulse
chmod 700 artifacts/audio-pulse
pulseaudio --daemonize=no --exit-idle-time=-1 --use-pid-file=no -n \
  --load='module-null-sink sink_name=quoridor_audio_test' \
  --load="module-native-protocol-unix socket=$PWD/artifacts/audio-pulse/native auth-anonymous=1"
# 別のshellで実行
xvfb-run -a env E2E_FIREFOX_HEADED=1 PULSE_SERVER="unix:$PWD/artifacts/audio-pulse/native" \
  E2E_BASE_URL=http://127.0.0.1:5186/ npm run test:audio:browsers -- --project firefox
```

Chromiumは共有インストールへのworktree内symlink、Firefox/WebKitはworktree内に取得。PlaywrightのFirefox/WebKit依存ライブラリとPulseAudioをコンテナに導入した。アプリのnpm依存は追加していない。

## 制約

- 実機Safari/iPhone/Android、実スピーカー/イヤホンでの聴感、OSの着信等による音声割り込みは未確認。
- 音声の実信号と消音は実際のGainNodeに接続したAnalyserNodeで確認した。画面状態や再生回数だけで可聴音が出たと判断していない。
- 同じoriginの複数タブで各タブが可視の場合、再生の排他制御は行わない。通常の背景タブは音声を停止する。
- main統合は並行作業側で行う。変更はこの専用worktreeに保持する。
