# リポジトリ全体の保守性レビュー（2026-10-06）

専用の独立レビューとして、現役入口から製品・研究・管理環境を静的に追った。実装の責務分離は概ね良い。優先する修正は、凍結候補と実際のtest入力の結合、shardを全RAM化する学習入口、cycleの直接起動時の子回収、現役テストを拾わない品質入口である。コードや研究条件は変更していない。

対象版は `main b2c2533d2e7c4632e5fa027f589e0b410b8b1444`。担当issueは `quoridor-8th`、レビュワーは `codex:/root/maintainability_reviewer`。以下の行番号はこの版に対応し、所見根拠のソースは `findings.json` の `source_manifest` でSHA256とbaseline一致を確認した。

## 範囲と限界

- `AGENTS.md`、READMEと既存の開発案内から、製品npm/Wasm入口、core/AI/Wasmのfeatures、TS bridge・Worker・session・描画・保存・test-support、対応e2e/test入口を確認した。
- 研究はcrate manifest、NNUE/特徴・探索境界、推論native build、runnerのconfig/admission/実行・失敗記録、Arrow/cacheのwriter/reader、Python model/config/cache/train/freeze/test/cycleと管理jobを確認した。
- 開発環境はDevContainer/build/post-create/toolchain、品質検査・ソースexport・資産解決・共有Beads/worktreeの実入口を確認した。全行・全過去runを読む監査ではなく、現役の呼出関係に基づく標本レビューである。
- ビルド、テスト、モデルforward、学習、対局、生成、GPU、環境取得、外部API通信、全Git履歴・巨大資産の走査は実施していない。RAM/時間の実測や、科学結果の再認定はしていない。
- 文書の一斉整理・知見統合・`.ignore`追加、`scripts/README.md`/`tools/README.md`の古いteam/scheduler/watch案内は `quoridor-d3g` が対応中。未対応の重複所見として数えない。過去recipe・凍結比較・研究データを、名前や件数だけでdead codeと認定していない。

## 所見

P1は実体と結果の対応を壊す問題、P2は現役の保守・検証・規模拡大を妨げる問題、P3は影響の小さい撤去・環境整理候補とした。優先度は修正開始や研究再開の許可を意味しない。

### MR-01 / P1: 凍結署名とtestで実評価するモデルが別の入力になっている

**根拠・呼出経路:** `python -m quoridor_training.train test` → `train.py:850`。`train.py:739–752`は同じstateから`.pt`とnative重みを出力するので、正常に完了した一回の学習直後は対応している。native manifestは`57–67`で尺度を含み、freezeは`792–810`でbest native manifest/weights・initial native weights・dataset SHAを保持する。

しかしtestの照合は`857–861`のbest nativeファイルだけで、評価は`866–888`の`config.json`、`scale.json`、`initial.pt`、`best.pt`を読み直す。結果は`909–915`でnative側の`weights_sha`を`candidate_sha`として掲示する。`scaled_model.py:49–55`の尺度、`residual_model.py:25–32`の尺度・距離係数は`persistent=False`であり、checkpointのstate_dictが尺度の変更を打ち消す保護もない。`data.json`の距離/定数基準も未結合である。

**根本要因・影響:** 候補の正本がnativeモデルなのに別の未署名checkpoint/設定からPythonモデルを再構成する。たとえば別runの同topology `best.pt`への取り違え、または`scale.json`の変更はnative署名を保ったまま実評価を変える。test結果のcandidate SHAは実評価した値の根拠にならない。現在の保存済み研究結果が実際に壊れたという証拠ではない。

**推奨範囲:** freeze/testを一つのmodel descriptorに統一する。Pythonで評価を続けるなら、実消費するcheckpoint・尺度・モデルconfig・target/基準・test bindingをfreezeへ結合し、評価前に検証する。initial/best両方を対象とし、nativeとの対応も検証可能にする。変更済み入力を評価前に拒否する小fixtureが適切である。

**確信度・未検証:** 高。静的なデータフローと非永続bufferを確認。外部の不変保存manifestが個別runを保護し得るが、この公開test入口は資産resolver/外側manifestを検査しない。NN実行での再現はしていない。

### MR-02 / P2: sharded学習cacheが全dense corpusをRAMにコピーする

**根拠・呼出経路:** `train.py:122` → `cache.load` → file入力時の`cache.py:119–121` → `_load_sharded`。childは`138–140`でmmapするが、`113`の`np.concatenate`がx/d/y全体を新しい連続RAM配列へコピーする。rowsも`131`で全JSONを読んでlist化し、shard統合時には`96–105`で追加dictを作る。`train.py:172–174`の「mapped on CPU」という前提はこの入口では成立しない。

**根本要因・影響:** shardを単なる一括配列結合として実装したため、batch転送が有界でもhost memoryは入力総数に比例する。特徴だけで1,000,000行 × 2 × 312 × 4 = **2,496,000,000 bytes**、3,000,000行なら7,488,000,000 bytesの新しいdense配列が必要で、metadata・元mappingのresident pages・Torch/optimizer等は別である。この計算はRSS実測ではない。大量入力へ進むとloader初期化がRAM枠や時間を消費し、科学本体に入る前に失敗し得る。

**推奨範囲:** cache APIをshard-awareなbatch取得へ変え、global indexから必要shard/batchだけを読む。hash/partition/露出検証は維持し、metadataも有界に扱う。既存の密配列APIを互換目的で恒久併存させずcallerを更新する。規模・選択方法を変更する実験は人間の判断を待つ。

**確信度・未検証:** 高。numpy concatenateとbyte算術による判断。OOM・throughput・GPU費は未測定。既存の小診断が失敗したとの主張はしない。

### MR-03 / P2: cycleの直接起動では中断時の子回収が完結しない

**根拠・呼出経路:** `quoridor-runner cycle`は`main.rs:128–136`でPython cycleを同期起動する。`cycle.py:22–30`は各stage子を別sessionにする。期限超過では`33–39`にTERM→KILL→waitがあるが、それ以外のexceptionでは`41–44`がTERMと3秒waitのみで、wait timeoutに対するKILL回収がない。cycleにはSIGTERM handlerがなく、`except BaseException` (`230–234`) はOS既定SIGTERMによる終了時には走らない。

**根本要因・影響:** timeout cleanupと一般中断cleanupが別実装で、後者が弱い。直接CLIをCtrl-C/SIGTERMで停止した場合、別sessionの学習子が親と一緒に停止する保証がない。子がTERMを無視する場合は一般exceptionのfinallyがTimeoutExpiredで抜ける。stageログも`21–25`で上限なしの直書きであり、outer jobのbounded tailはこれらのファイルを制限しない。RAM/output/pauseのconfigはRust generation/arenaには届くが、cycleのcache/train/test監視はdeadline中心で、全工程の同じ管理契約になっていない。

**推奨範囲:** cycle自身が子identityを所有し、timeout・signal・exceptionの全経路で同じTERM→KILL→wait処理を通す。stageごとの散在監視を一つのcycle資源/ログ/pause契約に揃える。CPU/GPU/NN予算を増やさず、人工短processの中断fixtureで確認できる。

**確信度・未検証:** 高（直接起動の欠落）、中（実際の残存範囲）。`research-job.py:253–255,275–313`は記録済みdescendantをidentity付きで回収するため、そのwrapper経路が常にorphanになるとは言わない。wrapper外の直接入口とcycle自身の保証不足を指摘している。実processを起動していない。

### MR-04 / P2: 研究の軽量品質入口が現役のNN0回帰テストを実行しない

**根拠・呼出経路:** `check-research.py:18–50`はtraining配下のPythonを構文・整形対象に含めるが、実テストは`121–127`で`quoridor_training.test_contracts`だけを指定する。`test_selected_target.py`、`test_residual_config.py`、`test_sampling.py`、`test_plotting.py`、`test_sharded_cache.py`の回帰検証は実行されない。selected-targetは`19–56`で型/欠測/teacher混合/列交換を、sharded-cacheはpartition/ID/順序/hashを検証する現役テストである。`test_observation.py`にはNN0クラスと、明示opt-inでTorch/モデルを使うクラスが同居する。

**根本要因・影響:** source発見はdirectory単位だがテスト発見は古い一module指定のまま。新しい保護を壊してもAST・format・既存contractが通る。整備済みテストが通常入口から見えず、人が過去runの個別実行手順を知る必要がある。製品`package.json:16`も既存`test:audio` (`20`) を含めないが、ブラウザe2eにはaudio試験があり完全無検証ではない。

**推奨範囲:** NN0 suiteを明示的に集約し、新規testの登録漏れを防ぐ。科学/モデル試験は許可を要する別入口に保ち、全`test_*.py`を無条件に起動する変更は避ける。製品の安価なaudio保存contractも製品gateで拾う。新実験やGPU試験の開始は不要。

**確信度・未検証:** 高。entrypointとtest定義の静的照合。テストを実行しての合否は未確認。

### MR-05 / P2: 製品checkがnative研究workspaceに依存し、対象を絞れない

**根拠・呼出経路:** `npm run check` (`package.json:16`) はrules/AI Wasm検証の後も、`cargo check/clippy --workspace`を各featureで繰り返す。workspace (`Cargo.toml:3–7`) はinference/data/runnerを含む。inferenceの`build.rs:3–8,93–94`はdefaultでもC++ ORT wrapperと`dl`をビルド/リンクし、runnerの`resources.rs:294–305`はLinux affinity APIを使う。

**根本要因・影響:** 製品gateとnative研究gateが一commandのworkspace選択に結合する。製品UI/保存の変更でもArrow・C++ compiler・Linux固有crateの準備や障害を引き受け、同じ研究workspaceをfeature別に検査する。製品だけの検査・復元環境を小さくできない。これはLinux研究workspaceの設計自体が誤りという指摘ではなく、gateの責務と運用費の問題である。

**推奨範囲:** shared Rust workspaceは維持し、製品gateのpackage集合とnative研究gateを明示する。両方が必要な統合検証入口から呼べる構成にする。rules/AIの別artifact、DTO/fixtures/strict TS検証は維持する。

**確信度・未検証:** 高（選択・依存）、中（利用環境ごとの支障）。ビルド時間やmacOS/Windows失敗は実測していない。

### MR-06 / P3: DevContainer起動が未使用Godotと研究専用環境の責務を抱えている

**根拠・呼出経路:** `devcontainer.json:2,8–11`はGodot名・binary/template設定、`Dockerfile:67–69`はGodot導入、`post-create.sh:35–38`はGodotを含むtoolchain更新とtraining setupを常時実行する。`update-toolchain.sh:57–104`はGodot/templateを取得し、`verify_env.sh:15,20–21`はgodot/gdlint/gdformatを必須とする。一方、現役sourceで`project.godot`/`.gd`/`.cs`は見つからず、`verify_env.sh:148–150`もproject不在を許す。image/update scriptはarm64を扱うが、`setup-training.sh:13`はx86_64以外で終了し、post-create全体を止める。

**根本要因・影響:** 元の環境templateの責務が現製品Rust/Webと研究の必須起動要件に残る。製品作業のコンテナ再作成でも未使用toolchain・templateの取得/更新、training依存準備、対応arch制約を背負う。最新stableを使う方針自体は問題にしていない。

**推奨範囲:** 実利用を確認してGodotの導入・更新・検査・dead headless入口をまとめて撤去し、製品共通初期化と研究環境取得を明示入口に分ける。研究に必要なNVIDIA/cache/永続volume/Beadsは保護する。環境変更は別保守タスクで行う。

**確信度・未検証:** 中〜高。source利用と起動chainを確認。実再作成・取得容量・時間は未測定。外部のGodot利用は不明。

### MR-07 / P3: 初期互換probe/APIがcallerなしで公開境界に残る

**根拠・呼出経路:** `quoridor-core/src/lib.rs:10–19`の`distance_to_goal`はphase0 probe専用で、現役source/test/scripts検索では定義以外のcallerなし。`quoridor-wasm/src/lib.rs:106–121`の`initial_position_json`はコメントが互換目的を明示し、rules artifactの公開exportとしてビルドされるが、TS bridge/製品/testのcallerは見つからない。現役の初期局面は`RulesGame::new/get_view`が扱う。

**根本要因・影響:** 過去互換の小さな公開契約を現在のDTO正本とは別の手書きJSON形式で維持する。実害は小さいが、不要なAPI/テスト要否を判断する負担と、初期局面表現の複数正本を残す。

**推奨範囲:** repo内callerの無い2入口を撤去する。具体的な外部利用が判明した場合だけ対象・撤去条件を明示して別判断する。標準ルール/GameやB0/MCTS/NNUE対照の現役機能は削除対象にしない。

**確信度・未検証:** 高（repo内callerなし）、中（外部caller不明）。公開Wasm ABIの外部利用は確認できていない。

## 保持すべき良い構成と全体判断

- ルールの正本はcoreで、Three.js/inputはRust viewと合法maskを利用する。Wasmはrules/AIを別artifactにし、同時featureをcompile errorにする。wire DTOの生成とnative/Wasm fixturesがある。
- Worker/clientはrequest・gameEpoch・revision・positionKey・generationを照合し、取消ack timeoutや再起動、session側の着手直前合法性確認を備える。単なるAPI形状検査に留まらず、stale reply、undo、restore、fault、pointer/keyboard等のe2eがある。
- Sigma研究contextのhistory/terminalは標準Gameと明示的に分かれ、NNUE/αβ/MCTS/推論queue/データ/runnerの依存は研究下層からframe固有recipeや管理scriptへ逆流していない。B0とNNUEを「重複」として一括削除する根拠はない。
- native runnerは失敗時にも予定slotをUNKNOWNで保持し、outcome/identity/admissionを新runへ保存する。backendにsilent fallbackを設けず、synthetic orchestration試験でfault・deadline・pause・join・既存出力保護を検証する構造がある。
- 資産resolver・source export・共有Beads lock・限定整形環境は正本と一時物を分ける。job controllerはbounded tailとidentityに基づく回収を実装し、応答不明の通知を成功に見せない。この外側保護はMR-03の直接cycle経路と区別する。
- `runtime.rs`（2067行）・`train.py`（948行）・`main.ts`（715行）は責務が集中するが、行数だけで分割を必須とはしない。先に所見の境界（artifact descriptor、shard batch取得、子管理、gate）を整理する方が、独立検証できる変更になる。`read_dataset`と`for_each_row`にはArrow検証の重複があるが、現時点の不一致は立証しておらず、reader共通化はデータ入口変更時に検討できる。
- Rust/品質Python/研究JSにはformatter入口がある。一方、製品TS/CSS、Shell/native C++まで覆う一つのformat/lint入口やhosted CIは今回確認した配置には無く、変更担当の限定整形に依存する。既存方針の遵守を自動化する余地はあるが、未整形変更やCI起因の現障害を再現したものではない。

文書数や研究資産量を理由に削除を勧めるレビューではない。研究の条件/規模を変更せずにまずMR-01・MR-03・MR-04の入力同一性と回収・検証境界を補修し、MR-02は大量入力の決定前に費用と実装範囲を具体化するのが妥当である。

## 検証・引渡し

検証はソース/呼出の読取、候補sourceのbaseline SHA照合、recordのJSON parse/schema・path/line整合、専用Prettierによる2recordの限定整形/checkである。実行合否やNN/GPU成功は報告しない。出力は本directoryの `report.md` と `findings.json` のみ。Rootが独立見直し・Git保存・issue受入れを行う。レビュワーはsource/docs/config/Git/indexを変更せず、引渡し時に書込STOPする。新しい修正や研究は自動開始しない。
