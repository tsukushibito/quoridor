# SIGMA-INFERENCE-PROBE / quoridor-4lc.11

試行1・契約版1、hypothesis / 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator。目標quoridor-4lc版1継承。保守起点19:50:15UTC、処理期限20:40:15、提出期限20:50:15。自.6は統括の参照生成限定受入れとcritic .8の再生成一致を確認して本人close。.11は受入れ待ちin_progress。

問いは固定NNを共通Rust backendでnative/Wasm実行できるか、分離ORTとB0維持のどちらへ投資するか。観測: tract-onnx固定0.22.3はnative compile/run、wasm32 compile/既存Chromium153実runとも28件を通過。各3836要素の事前gate abs≤1e-4+1e-4×abs(reference)、shape/finite/value範囲を保持。native最大abs9.775161743e-6、Wasm1.049041748e-5、失敗要素各0。参照はORT1.30.0/Numpy2.5.3、CPUExecutionProviderのみ、intra/inter1、SEQUENTIAL、BLAS等1、CPU0。2独立プロセスの参照出力はbyte一致SHA256 060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a。ORTには待機helper OS threadも存在し、そのCPU delta0を記録。独立役による検証ではない。

入力はONNX d790…908d/11,663,428bytes、Sigma7511863…、fixture206f…bffb/28件（合法20・人工8）。648floatをfloat32[1,8,9,9]へ順序維持、実graph全179node属性を保存。P2 permutation/合法Action→Rust209/priorを参照fixtureから診断、prior最大absはnative6.2532e-7/Wasm1.0762e-6。終端NNは数値診断だけで探索適用しない。Rust特徴生成・履歴・backupは本probeでは検証していない。

競合案: A共通Rustは同期Evaluator契約を維持し、モデルplanを1回load、研究context特徴→136canonical logits→P2写像→合法softmax→手番valueへ接続できる予測を支持。Wasmのブラウザentropy importは0回呼出し。B分離ORTは参照Python CPU実行とSigma Web一次コードで根拠を得たがRust ORT binding/Web ORT同モデルの新実行は未試験。現Evaluator::evaluateは同期であるため、Webのasync session.runにはpending leaf保持/外部評価結果の継続・キャンセル境界、136↔209とvalue検査の共通化が必要。公式Web設定はnumThreads=1/wasm providerへ固定が必要。C B0維持は新依存・非同期境界の費用0の対照だが固定NN互換は提供しない。Aの同期性は有利との推測であり、速度・棋力優位の観測ではない。

失敗は補助実装/起動: native shapeマクロ、getrandom target設定、Wasm host import、既存Chromeパス、専用TMPDIR socket長。それぞれ原因修正後1回だけ再試行、ログ保持。モデル演算変更0、negative numeric result0。版0.22.3公式サンプル使用で最新0.23.8や将来APIは未試験。debug artifactはnative76,401,984/Wasm36,970,550bytes、Wasm linear memory38,273,024bytes。release容量/速度/製品メモリとキャンセル未検証。製品コード/root lock/共有環境は編集0、.10のAI source hash変化は別入力としてmanifest記録。

資源・逸脱: 新規保存は保守的logical約1.415GB、2GiB残約0.732GB。専用再実行の全子RSS観測最大1,270,988,800bytes、各TID CPU0。累積観測CPU下限約139.8秒、初回Chrome子CPU等は欠測。初回ブラウザが標準/tmpへ一時profileを書いた境界逸脱と旧監視の子RSS不足を明記する。自動終了清掃済み、専用領域で同出力再現したが全試行の上限遵守は認定しない。GPU/学習/対局/モデル再取得/追加委譲0。

再現はtools/ai-sigma-inference-probe/README.md。詳細は .artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/{manifest,ort-repeat,native.gate,wasm.gate,prior-action-diagnostics,storage-process-final}.json とstage別log/process.json、独立Cargo.lockの全checksum。一次根拠は版付きSonos tract README/example、公式ORT threading/Web optionsの保存snapshot。成功は自己再実行のみ、統括+criticの独立受入れは未実施。全自己PID/子PID終了・残存0、port開設0、手動証拠削除0。最終証拠保存後に書込み停止しpause確認/backup/reportする。次はAの独立gate再検証と小さいEvaluator接続・release/Worker制約試験を別契約で提案する。Bを安全な後退案として残し、製品採用/棋力到達を認定しない。
