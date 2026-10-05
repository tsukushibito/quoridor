# SIGMA-MODEL-ACQUIRE / 試行1 / 契約版1

目標quoridor-4lc、子issue quoridor-4lc.9。steward / 01a0f31d-99ee-7d63-b162-bc1a59c457c6 → coordinator。契約: ../design/ai-sigma-contract-steward-model.md、目標契約版1。作業場所ai-sigma/codex/ai-sigma。

観測: 固定commit 751186344fc52ad0c29bc65922e62c6fa915f006のONNX1件を研究用保存先 models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx に取得。実11,663,428 bytesとGit blob f23802a83dc9054b5227da74b3771698854535f0が期待に一致。SHA-256はd790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。HTTP200、最終URL同一、retry0。

静的結果: 既存Python3.14.7/onnx1.23.0、external load無効、checker通過。IR8/opset17、FLOAT input[1,8,9,9]、policy_logits[1,136]、value[1,1]で全宣言一致。179nodes/16演算種類、FLOAT initializer83件・raw11,633,196 bytes、外部重み0。仮説はsize/blob/静的宣言の範囲で支持。NN出力・速度・棋力・backend互換性は未確認で採用しない。詳細はJSONへ。

notice: 保存済み原文MIT LICENSEをhash照合し同梱。PCR250はexport原文/履歴の宣言。モデル固有配布条件・第三者重み不在・PT対応は未確定、製品再配布の包括的許可を断定しない。

資源: CPU0のみ/RLIMIT_AS1GiB、peakRSS87,068KiB、取得+解析CPU約0.346秒、GPU/NN/学習0。取得PID660293・解析660304は各60秒上限、19:39:38UTCまでにexit0でwait回収、残存なし。experiment .7のCPU2を使わず、無負荷認定なし。開始前空き517,729,607,680 bytes、既存cache11,718,397,952 bytes。所有別量と集計限界はmanifestへ。新規量/128MiB残量はstorage.json。追加取得・依存同期・torch/ORT import・削除なし。

初回操作19:31:29UTC。turn開始値未取得のためissue作成19:26:15を保守的起点にし、処理19:44:15/報告19:51:15を締切として実時刻管理。暫定報告を先に保存した。取得/静的解析は期限内。実装失敗/研究negative resultなし、独立再実行は未実施。再現script・入力/lock/script hash・HTTP/PID/終了logは .artifacts/ai-sigma/runs/SIGMA-MODEL-ACQUIRE/{manifest,graph,processes,storage}.json を参照。

モデルとrun/reportの書込みを最終記録後に停止。証拠はモデル・notice・hash・graph・logを保持、削除0。自.3は受入れ確認してclose。.9は受入れ待ち、目標/他者issueは閉じない。pause確認・backup後にreport送信。次は互換性/数値一致試験を別契約へ。
