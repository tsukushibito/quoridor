# 枠10 baseline対固定Sigma：ユーザー方向変更による停止

ユーザーの研究方向変更に従いgroup6の安全な終了・回収・保存後に停止した。group7〜16は未開始。途中成績を停止理由に使っていない。忠実Sigma-Web Rust/Wasm基準候補を優先する次課題は別契約であり、本課題では新kernel/build/NNを開始していない。

## 全予定64枠の結果

| 分類 | 枠数 | score扱い |
| --- | ---: | --- |
| 正常goal：候補勝 | 3 | 1 |
| 正常goal：候補敗 | 17 | 0 |
| 正常draw | 0 | .5 |
| group1 Node OOM・実開始/結果欠測 | 4 | [0,1]未知 |
| ユーザー方向変更による中止・未開始 | 40 | [0,1]未知 |

運用主scoreとterminal手品質の**全64識別区間は共に[0.046875, 0.734375]**。正常終局のみの補助平均は3/20=.15（選別された20枠、主分母への置換なし）。候補色1は2勝8敗、色2は1勝9敗。完了10pairは両色候補敗7pair、同盤面side勝者・両AI一勝ずつ3pair。未知22pairを落とさない。

事前固定の独立bounded32pair追加仮定のHoeffding eps=0.240080697830を外側に加えた参考区間は[0, 0.974455697830]。独立性・被覆は立証しておらず、.5を跨ぐ。固定集合全体の棋力差は未確定。20正常局の偏りを一般棋力・NI・Sigma同等・119敗因・係数因果へ換算しない。

## 入力・政策・時計

32prefix/64slotをAI前に固定した。4/5/12/13ply各8slot、seed正本SHA a82f2d01875180aa6a4a53be6e62d1ae11b9ab01ef2b3d37e5a1b40a7ede5c04、全8attempt規則。旧119のkey＋正規化history_counts＋side完全signatureを全8一律除外。32/32初attempt合法非終端、旧一致0、新重複0。原preregister・入力SHA71505c5d56aa775938d00aec4e1fc10f10bac6bed5921411a8649936d95445b2・層/色/順を保持し、補充/再試行/置換0。

candidate immutable Q0/C1.5と原fixedSigma C1/FPU.2/temp0、同ONNX/ORT1.21 CPU各1thread/探索seed1979、CPU[2]単logical。T500/cutoff402/adopt411/bounded2sample。2専用Worker/session/SAB/control/generation、main RuleA審判・時計、Node外起動監視と局終了後保存のみ。相手t0を旧ACKの前提にせず自次手前だけ自旧zero、確定後旧返却discard。製品政策変更0。

完了pair3〜12の10初根対応は保存key/history/prefix/model/feature bits一致、137保存数値完全一致（新golden無し）。pair1/2はOOM欠測、pair13〜32は未開始。深部一般一致や独立ルール証明ではない。

## 分母と費用

| 完了20局の保存分母 | candidate | fixedSigma |
| --- | ---: | ---: |
| 手要求 | 600 | 607 |
| 手API開始/返却 | 5397/5397 | 6364/6364 |
| 採用CP completed backup合計 | 5382 | 7525 |
| 採用CP completed NN合計 | 4897 | 5872 |
| 旧返却discard | 323 | 321 |

startup36/session12は6job分として手分母と別。group1手費用/CP/通常NNzero receiptは欠測、0にしない。採用backup−NNの導出値は候補485/参照1653だが、terminal-noNNの直接分母・cap/pseudo leafの内訳は未記録。API awaitはkernelCPUではなく、異状態のNN総量比も同仕事量/同CPUの証明ではない。保存時計/旧ACK/自己待ち/残wallはaggregateに保持。clock中間drift/exact atomic store/純NNCPUは未測定。

生成・初期化・失敗・監視込み管理heavyは735.277198秒/7200秒、各job600秒内。guarded static 4.045497秒と保存helper 29.330510秒を別記し、未記録の軽い読取費/全team費は未知。最大観測currentRSS 1885872128bytes、40ms標本は瞬間peakや全期間公平cycleを保証しない。Node heap192MiBから768MiBへ局終了後保存を修復したがRAM6GiB/guard5.5GiB内、探索/入力/時計規則変更0。

## 失敗・停止・保存

group1版44d37c7はNode OOM/exit-6。4予定枠の実開始/結果と通常Modeldrop/NNzero/mainreceiptは欠測、guardianのowned物理回収とは分離した。科学source c29c662a0ae53e0fce782a86abfbe1686eccb7d7以後は1局ごと終了時の全rawを保存し、4局最終収集はcompact化。保存payload NN0mockと旧失敗logを保持、成功game再実行0。

最後group06開始2026-10-03T01:06:27.631043UTC、終了01:08:34.928350UTC、exit0、保存Git8448e20316d96dffe623ab6a6e4cedd21fdd5f2d。controllerは01:08:43.898951に全自子wait後return、Beads paused-by-userによりgroup07前拒否、signal/interrupt0。各group正常Model2/search/main timer-message/monitorcallback/innercontrolledzeroとouterownedwait remaining/unknown空を停止正本に分けた。現在sameidentity不在は自然終了/全host/全期間保証ではない。

科学source/結果書込停止速報を本文より前に配送した。最小pack/Git/backupの記録helperは別。6archiveの全member SHA-size復元と元rawからscore再算を確認した（自己検査、独立科学受入れはcoordinator）。旧結果/期限を書換えていない。残る149 heavy開始は禁止、次案はユーザー指定の忠実Sigma-Web Rust/Wasm基準候補の別契約のみ。現独自政策の採用/係数変更・新実行を自動開始しない。

再現参照: `research-data/ai-sigma/frame10-baseline-gap/preregister.json`、`inputs.json`、`aggregate.json`、`stopped-data-verification.json`、`final-cost-ownership.json`、`user-direction-science-stop.json`。各group manifestに実source/servedhash/command/config/memberを保存。最終handoffのGit/stop/archive/backupにbindする。旧119/117のWDL混合0。
