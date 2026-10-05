# 固定Sigma ONNXの研究用取得・graph・資源確認

Beads quoridor-4lc.9 / SIGMA-MODEL-ACQUIRE / 試行1 / 契約版1。目標契約 [版1](ai-sigma-research-goal.md)を全文継承。通常の研究用固定モデル取得は既存ユーザー許可内。担当steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6、報告先coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。

## 問い・仮説・対照

固定Web ONNXを同じbytesとして取得し、現候補backendの演算互換性検討へ渡せるか。宣言されたschema/opsetと実graphが一致するという仮説。対照は固定treeのsize/blobと保存済みexport原文。違えば取得/参照不成立として止め、別モデルへ置換しない。NN出力・棋力・速度はこの静的試験から判断しない。

固定commit 751186344fc52ad0c29bc65922e62c6fa915f006。URL https://raw.githubusercontent.com/bartolomeo3000/SigmaQuoridor/751186344fc52ad0c29bc65922e62c6fa915f006/docs/models_9x9/best.onnx 。期待11663428 bytes、Git blob SHA1 f23802a83dc9054b5227da74b3771698854535f0。blobの検算はSHA1(b'blob '+decimal_size+b'\0'+bytes)でありファイルSHA1と区別する。実SHA256を取得後固定する。入力資料 .artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/{model-manifest.json,source-manifest.json,sources/,fixtures.json} と docs/reports/ai-sigma-hypothesis-parity.md（3f2a7ccce82552bca670b3e518fda84953f15421623504ceef9d34a9d6143460）、critic-profile-parity.md（0a3fe219707369414f09cf1d2ef4be6b0937a97d2866d2959591316b80c48837）。実在snapshotの名前は限定確認する。root MIT noticeと未確定provenanceを保ち、製品再配布の包括的許可を断定しない。

## 所有・書込み・固定環境

作業場所 /workspaces/quoridor/.worktree/ai-sigma、codex/ai-sigma。主checkout/他worktree/実験担当source/旧artifactは保持。唯一の書込み範囲 models/experiments/ai-sigma/reference/sigma-pcr250/、.artifacts/ai-sigma/runs/SIGMA-MODEL-ACQUIRE/、docs/reports/ai-sigma-steward-model.md。.gitignoreは既にmodels/experiments/あり、通常編集不要。ダウンロード前にgit check-ignoreとstorage policy全文を確認。apps/web/public/modelsへ置かない。

Pythonは既存 /home/vscode/.cache/inference/envs/quoridor-training/bin/python を-B/PYTHONDONTWRITEBYTECODE=1で読取利用し、onnxの静的load/checker/graph型だけ使用。torch import、NN推論、ORT session、GPU、PT取得、clone、依存sync/install、環境更新、全体走査、追加委譲はなし。依存version/lock hashesを記録。ONNXのexternal_dataがあれば検出して自動外部取得はせず、load_external_data=Falseで安全な静的解析に留める。

## 資源・期限・終了

開始は実send/turn開始UTCを保存し、25分以内、全体2026-10-01T01:17:58.145139Z以内。処理の期限は開始+18分、残7分は短報告/停止/Beads/reportへ予約。開始時に短い暫定報告を作り、18分で未完成でも追調査を止め既知結果だけ提出する。報告上限日本語1500字程度、詳細は機械manifestへ。保存/通信まで含むdeadlineを確認し、超過を成功にしない。

CPU0単一、RAM1GiB、GPU0、新規保存全体128MiB（取得途中と最終の同時保持含む）。チームはexperiment .7準備最大2CPU/RAM4GiBと本役1CPU/1GiB、統括短い操作でCPU計算枠4/RAM8内。正式速度窓に重い処理を重ねない。取得は約12MBの1件、短い解析のみ。.7の計算条件/競合へ黙って無負荷認定を加えない。CPU2/3では動かない。全チーム新規12GiB枠、実験所有2GiB予約と本128MiBは別、初期旧cache10.81GiBは新規へ二重計上しない。開始前に対象/空き容量を限定du/dfで記録し、12GiBを超えそうなら取得停止、既存物を消さず報告。

取得子processはtimeout最長60秒、response最大13MiB、固定URL/redirect最終URL/status/content-length/実bytes/UTC/PID/exit/hashを保存。リトライは通信失敗のみ最大1回、理由と部分証拠を保持。モデルbytes/hash不一致はリトライで隠さず停止。解析子は60秒以内・CPU0、可能ならresource RLIMIT_AS/RSS guardで1GiB上限、実peak記録。バックグラウンド化しない。pause/異常では自己子だけ停止・wait、PID/終了状態/失敗証拠を保持、共有processは停止しない。削除0。

## 成果物・受入れ

immutable取得manifestにURL/commit/期待size/blob/実SHA256、license notice/hash/追加条件未確定、source lineage、localpath/bytes、graph IR/opset各domain、input/output名・shape/dtype、全op種類・個数、initializer型/size/external情報、checker結果、CPU/RSS/toolversion、取得command/終了を記録。graphの入力8x9x9/136policy/valueの宣言との一致/不一致を明記し、backend互換性は演算一覧だけから完了扱いしない。特徴schema/action/value視点は参照conversion-contractへリンク。元全payloadをコピー不要、参照hashで保存。

対象別の新規保存量・既存cache量・空き容量を1回ずつ集計。測定時刻のworktree duから17:17増分を正確復元したと主張しない。所有runごとに合算/重複の限界を残す。原artifactはhash維持。

開始ready/show目標と.9、claimは.9だけ。受入れ済み.3は根拠追記して本人close可。目標/.1/他担当issue変更禁止。終了はsource/モデル書込み停止・全自process回収後、目標/.9pause再確認、backup sync、主入口report --to coordinator --issue quoridor-4lc。.9は統括受入れ待ちでcloseしない。通信acceptedと成果受入れ/モデル採用を区別する。
