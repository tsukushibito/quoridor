# リポジトリ全体の保守性レビュー（2026-10-06）

専用の独立レビューとして、現役入口から製品・研究・管理環境を静的に追った。実装の責務分離は概ね良い。優先する修正候補は、凍結候補と実評価入力の結合、TensorRT exportによる既存asset破壊の防止である。全体停止・遅い設定不適合・cache検証・規模拡大費・品質入口・導線についても大小の独立した所見を挙げた。コードや研究条件は変更していない。

拡張レビューの対象版は `main 4494564ff7f28148fab6e1205cb83aeb3e980d77`。原7所見は `36f553ed69ef7a4f8abf4b98669e29ed0e01bc40` に保存済みで、本文・JSON所見を保持した。同セッションでユーザーの追加指示に基づき主要subsystemの未読経路と失敗境界を広げ、件数目標を置かず独立原因ごとに追加した。担当issueは `quoridor-8th`、レビュワーは `codex:/root/maintainability_reviewer`。原7所見のsourceも現在版とのbyte一致を確認した。以下の行番号は現在版に対応し、所見根拠のソースは `findings.json` の `source_manifest` でSHA256とbaseline一致を確認した。

## 範囲と限界

- `AGENTS.md`、READMEと既存の開発案内から、製品npm/Wasm入口、core/AI/Wasmのfeatures、TS bridge・Worker・session・描画・保存・test-support、対応e2e/test入口を確認した。
- 研究はcrate manifest、NNUE/特徴・探索境界、推論native build、runnerのconfig/admission/実行・失敗記録、Arrow/cacheのwriter/reader、Python model/config/cache/train/freeze/test/cycleと管理jobを確認した。
- 開発環境はDevContainer/build/post-create/toolchain、品質検査・ソースexport・資産解決・共有Beads/worktreeの実入口を確認した。全行・全過去runを読む監査ではなく、現役の呼出関係に基づく標本レビューである。
- 非科学2行fixtureのnumpy/cache parserのみ実行し、MR-14の受理挙動を確認した（NN0、model importなし）。ビルド、runtime/model試験、モデル初期化/forward、学習、対局、生成、GPU、環境取得、外部API通信、全Git履歴・巨大資産の走査は実施していない。RAM/時間の実測や、科学結果の再認定はしていない。
- 文書の一斉整理・知見統合・`.ignore`追加、`scripts/README.md`/`tools/README.md`の古いteam/scheduler/watch案内は `quoridor-d3g` が完了済み。未対応の重複所見として数えない。過去recipe・凍結比較・研究データを、名前や件数だけでdead codeと認定していない。

## 所見

P1は結果の帰属または保全assetを壊す問題、P2は現役の正しさ・保守・検証・運用枠を妨げる問題、P3は影響の小さい導線・診断・整形・証拠・撤去候補とした。優先度は修正開始や研究再開の許可を意味しない。

| ID    | 優先度 | 独立した問題                                                                        |
| ----- | ------ | ----------------------------------------------------------------------------------- |
| MR-01 | P1     | Frozen native SHA does not bind the checkpoint and scale actually evaluated by test |
| MR-02 | P2     | Sharded cache concatenates the entire dense corpus into RAM                         |
| MR-03 | P2     | Direct cycle interruption has weaker child cleanup than its timeout path            |
| MR-04 | P2     | Lightweight research gate omits maintained NN0 test modules                         |
| MR-05 | P2     | Product check selects the complete native research workspace                        |
| MR-06 | P3     | DevContainer startup still requires unused Godot and unconditional training setup   |
| MR-07 | P3     | Initial compatibility probe and Wasm JSON API have no repository callers            |
| MR-08 | P2     | AOTIの初回warm forwardがNN費用へ計上されない                                        |
| MR-09 | P2     | paired arenaのsplitを試合単位で割り当て、family検査で後から失敗する                 |
| MR-10 | P2     | benchmarkの全体停止条件が一探索の実行中に反映されない                               |
| MR-11 | P1     | TensorRT exportの一時ONNXが既存兄弟assetを上書きして削除する                        |
| MR-12 | P2     | residual学習を受理するcycleがarenaではv1/v2 Model loaderに渡す                      |
| MR-13 | P2     | ResidualModel loaderだけmanifest/weightsの上限検査前に全fileを読む                  |
| MR-14 | P2     | native cache readerは必要hashとfeature/distance対応を必須にしない                   |
| MR-15 | P2     | worktree helperの管理rootが呼出checkoutによって変わる                               |
| MR-16 | P3     | 旧固定run向けguardianがほぼ同じ2scriptとして残る                                    |
| MR-17 | P2     | production検証が通常distをtest API付きsubpath buildへ置き換える                     |
| MR-18 | P3     | 手書き言語全体の限定整形を実行する入口と対象一覧が揃っていない                      |
| MR-19 | P3     | 描画assetのfallbackで失敗原因がdiagnosticsから失われる                              |
| MR-20 | P3     | 現役環境報告から参照する13枚の画面証拠が指定保存先に無い                            |
| MR-21 | P2     | time-limited探索でもbenchmarkがfixed_work=trueと報告する                            |
| MR-22 | P3     | runner helpは未実装dataset importを案内しevaluateを省く                             |
| MR-23 | P2     | pagehideで不可逆disposeし、保存されたページの復帰経路が無い                         |

MR-01〜07は原レビュー、MR-08以降は今回追加した所見である。条件付き所見・既存の保護・未測事項は各項で分けている。

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

### MR-08 / P2: AOTIの初回warm forwardがNN費用へ計上されない

**発生条件:** AOTI backendで新しいbatch sizeを初めて使う。

**根拠・呼出経路:** `crates/quoridor-inference/native/aoti.cpp:60–79`、`crates/quoridor-runner/src/runtime.rs:1173–1182`、`crates/quoridor-runner/src/bin/teacher-qualify.rs:171–173`。native state(batch)はrun()を70・71行で2回呼びsynchronizeする。一方runnerは公開inferのnだけnn_callsへ加え、backend_warmup_nnの追加はcuda-tensorrtに限定する。AOTIの初回追加2nをこの集計は含めない。graph captureでも77行でrunを呼ぶが、captureを追加の実GPU forward数とは認定しない。

**既存の保護:** 通常infer件数・batch histogram・所要時間は記録される。teacher-qualifyにはTRTのB1–8 warmを36 NNとして明示加算する別保護がある。この所見はTRT全入口の計上欠落を意味しない。

**根本要因:** backend内の物理forwardとrunner側の論理request数を、backend名による特例で結合している。

**影響:** AOTIを含む全作業費・NN予算・backend比較が論理requestのみの値になり、初回batch種類数で未記録費が変わる。capture setup費は別の未測事項。過去の科学結果が実際に誤認定されたとは判断していない。

**推奨範囲:** backendがlogical/warm/capture/failed forward数を返す共通計数契約にし、runner・qualification・benchmarkで同じ項目を保存する。補正のための追加forwardは不要。

**確信度・未検証:** high。native/Rustの呼出と加算を静的照合。GPU実行・物理計数・capture費・歴史runの再認定は未実施。

### MR-09 / P2: paired arenaのsplitを試合単位で割り当て、family検査で後から失敗する

**発生条件:** 2 engine・偶数試合のarenaでtrainまたはvalidation境界が奇数になる。8 gamesの既定計算はtrain=5、validation=1。

**根拠・呼出経路:** `crates/quoridor-runner/src/runtime.rs:426–480`、`crates/quoridor-runner/src/config.rs:193–216`、`crates/quoridor-data/src/lib.rs:641–645`。plannedはid/2をfamilyにし、色交換の兄弟が同じopeningを使う一方、splitは個別idとtrain/validation数で決める。8 gamesではid4/5がfamily2でtrain/validationへ分かれる。configのsplit合計検査はfamily境界を検査しない。DatasetWriter.finishはstreamed family crosses splitとして拒否する。

**既存の保護:** dataset writerの厳格なfamily検査は漏洩したdatasetの完成を防ぐ。arenaの偶数games・2 engine検査と、正しい偶数splitを明示する運用もある。

**根本要因:** paired planの分割単位とdatasetの独立単位が異なり、事前設定検査が後段writerへ委ねられる。

**影響:** 正常に受理された設定で対局費を支払った後、dataset最終化に失敗しrunが完結しない。単にデータ漏洩が黙って通るという指摘ではない。

**推奨範囲:** family単位でsplitを計画するか、arenaデータの用途を明示し、paired境界を科学実行前に検査する。小さなplan算術fixtureで検証する。

**確信度・未検証:** high。8-game設定の整数算術と呼出の静的照合。対局を実行していない。

### MR-10 / P2: benchmarkの全体停止条件が一探索の実行中に反映されない

**発生条件:** 直接benchmark入口で一repeatがwall/deadline/pause/RAM境界を越える、またはbackendが長く停止する。

**根拠・呼出経路:** `crates/quoridor-runner/src/runtime.rs:494–505`、`crates/quoridor-runner/src/runtime.rs:1444–1504`、`crates/quoridor-runner/src/runtime.rs:1521–1529`。guardはrepeat開始時だけ。MCTS advance/infer loopには全体guardがなく、alphaへ渡すcancelはfalseのまま誰も更新しない。alphaの任意time_msは全体deadlineとは別条件。recordsは全repeat終了後だけresult.jsonへ書かれる。

**既存の保護:** MCTS/alphaにはnode/depth等の有限上限、alphaには任意の探索時間制限がある。外側research-jobで起動すれば管理側停止がある。これらは直接入口の全体pause/deadlineを探索中に反映する保証とは別。

**根本要因:** benchmarkが自己対局の監視・失敗記録経路から外れ、境界検査と探索cancelを接続していない。

**影響:** 一探索中に許可された壁時計/RAM枠を越えて処理が続き得る。中途failureでは完了済みrepeatの記録も失われ、原因と投入費の回収が難しい。無限loopや既往の超過実測を主張しない。

**推奨範囲:** 共通monitorからcancelへ接続し、MCTSの有界advance間で全体条件を確認する。進行・失敗・完了済みrecordsを有界に保存する。同期native呼出の停止保証は外側jobのexact cleanupと区別する。

**確信度・未検証:** high。静的なguard/cancel/保存経路の確認。長時間探索・停止processは起動していない。

### MR-11 / P1: TensorRT exportの一時ONNXが既存兄弟assetを上書きして削除する

**発生条件:** 新しいsigma.engineをexportするdirectoryにsigma.onnxがある、またはTensorRT出力名をsigma.onnxにする。

**根拠・呼出経路:** `tools/model-export/export.py:26–27`、`tools/model-export/export.py:60–89`。存在拒否はargs.outputのみ。一時入力はoutput.with_suffix('.onnx')を直接使いexport後unlinkする。sigma.engineの兄弟sigma.onnxは上書き対象になる。出力自体が.onnxならtemporary==outputとなり、engineを書いた83行の直後84行でそのengineを削除し89行のSHA取得へ進む。

**既存の保護:** 通常の未使用.engine名かつ同stem ONNXが無い場合は衝突しない。最終outputの既存拒否はあるが、この一時pathの所有は検査しない。

**根本要因:** 入力assetと一時物を拡張子置換だけで命名し、一時物の排他的所有を確立していない。

**影響:** 別exportや検証用ONNXを失う、または高価なexport後に最終artifact自体が無くなる。未保存モデルassetの破壊につながる入口上の欠陥。

**推奨範囲:** 専用TemporaryDirectory内の所有済み一時ONNXを使い、最終artifact/manifestを衝突検査して公開する。output拡張子衝突もモデル初期化前に拒否する。既存assetを触らないpath fixtureで確認できる。

**確信度・未検証:** high。Path変換・書込・unlink順序を静的確認。Torch/export/GPUは起動していない。

### MR-12 / P2: residual学習を受理するcycleがarenaではv1/v2 Model loaderに渡す

**発生条件:** cycleのtraining configに現在validate_configが受理するdistance_residualを指定してarenaまで進む。

**根拠・呼出経路:** `python/quoridor_training/common.py:115–130`、`python/quoridor_training/train.py:77–100`、`python/quoridor_training/cycle.py:163–173`、`crates/quoridor-runner/src/runtime.rs:391–402`、`crates/quoridor-nnue/src/lib.rs:205–208`、`crates/quoridor-runner/src/bin/nnue-diagnose.rs:282–284`。trainはresidual-v3 descriptorをexportするがcycleは常にkind=nnueへ設定する。runnerのnnue evaluatorはModel::loadを使い、そのloaderはQF1 scaled v1/v2だけを受理する。

**既存の保護:** loaderは未知schemaを拒否するため、別モデルを黙って評価しない。ResidualModel/ResidualEvaluatorとnnue-diagnoseの明示residual経路は存在し、residualがリポジトリ全体で未対応という意味ではない。

**根本要因:** 学習architectureと下流engine/loaderの適合をcycle admissionで表現していない。

**影響:** 生成・学習・testを終えた後のarena初期化で拒否され、許可済みcycleを完了できない。失敗が高価なstageの後へ遅れる。

**推奨範囲:** 共有model descriptorから対応loaderを選ぶか、residualが診断専用ならcycle開始前に明示拒否する。どの経路を製品/研究として支えるかは現行責務に沿って決め、新しいモデル研究を自動開始しない。

**確信度・未検証:** high。config→export→cycle→loaderの静的照合。residual学習/arenaは未実行。

### MR-13 / P2: ResidualModel loaderだけmanifest/weightsの上限検査前に全fileを読む

**発生条件:** 診断CLIのresidual pathに大きな誤入力manifest、または期待長より巨大なweightsを与える。

**根拠・呼出経路:** `crates/quoridor-nnue/src/residual.rs:93–119`、`crates/quoridor-nnue/src/lib.rs:139–155`、`crates/quoridor-runner/src/bin/nnue-diagnose.rs:282–284`。ResidualModel::loadはfs::readの後でmanifest64KiB上限、weights長/SHAを検査する。通常Model loaderはtake(65537)とweights metadata/有界readを使う。

**既存の保護:** residualにもtopology・正確な長さ・SHA・有限値・perspectiveの検査がある。正常モデルは有界で、異常入力を受理する問題ではない。quantized loaderも有界読取を持つ。

**根本要因:** 共通のasset reader契約がresidual loaderへ適用されていない。

**影響:** 誤入力を拒否するまでにfile総量のRAMを割り当て、モデル検査以前にOOM等で診断を失敗させ得る。

**推奨範囲:** manifestとweightsの有界readerを共通化し、サイズ確認・上限+1読取・exact-length/SHA検証を全loaderで維持する。

**確信度・未検証:** high。loader順序と既存bounded loaderの静的比較。巨大file読取/OOMは実施していない。

### MR-14 / P2: native cache readerは必要hashとfeature/distance対応を必須にしない

**発生条件:** directory cacheのcache.jsonが必要sha項目を欠く、またはx/dがrows metadataと異なる有限tensorである。

**根拠・呼出経路:** `python/quoridor_training/cache.py:116–143`、`python/quoridor_training/cache.py:17–34`、`python/quoridor_training/train.py:122–126`。readerはsha256 mapに存在する項目だけ検査し、空mapを受理する。dense xはfiniteのみ、distanceもfiniteのみで、rowsのsparse feature/STM distanceとの一致は検査しない。trainの後段検査は選択target列である。2行の非科学fixtureで空hash、x=.25、metadataと異なるd=.9、manifest不変でx=.75への変更がすべて受理された。

**既存の保護:** 通常Rust cache writerは正しい必要hashを保存する。非finite、row ID、test split、target検査はある。sharded child入口にはsparse/binary/distance対応検査があるため、その保護をnative directory全体に無いと一般化しない。

**根本要因:** manifestのhash mapを検証対象の任意一覧として扱い、実消費する必須fileとrows/tensorの一つの入力契約にしていない。

**影響:** 壊れたmanifestやcache作成変更で、記録した局面と別の入力特徴から学習できる。誤入力を科学処理前に拒否できず、署名なしtensor変更も検出できない。現存datasetの破損を立証したものではない。

**推奨範囲:** schema、必須file/hash集合、dtype/正確な長さを要求し、sparse feature・binary値・distance対応をchunk単位で確認する。sharded/nativeで同じ入力契約を使う。

**確信度・未検証:** high。NN0 numpy/cache parser fixtureで受理を確認。Torch/モデル/forward/科学datasetは未使用。receiptは本JSONのverification_resultsへ保存。

### MR-15 / P2: worktree helperの管理rootが呼出checkoutによって変わる

**発生条件:** managed worktreeをcwdとしてmanage_worktree.sh create/verify/lock-existing/removeを呼ぶ。

**根拠・呼出経路:** `scripts/dev/manage_worktree.sh:4–5`、`scripts/dev/manage_worktree.sh:16–25`、`scripts/dev/manage_worktree.sh:64–70`、`scripts/dev/beads-env.sh:4–6`、`scripts/dev/research-session.py:90–112`。helperはgit --show-toplevelを正本rootにし、その下の.worktreeを管理対象にする。linked checkoutではそのcheckoutがrootになり、createはnested .worktreeへ、managed_recordsは既存のmain管理pathを対象外にする。共有Beads/session側はcommon-dirからmain rootを解決している。

**既存の保護:** main cwdでの操作は期待どおり。name検査、Git worktree登録・lock、volume検査等はあり、誤rootが直ちに共有DB削除を意味するものではない。

**根本要因:** 管理namespaceにcurrent checkout rootとcommon repository rootを混用する。

**影響:** 同じhelperが利用場所で別集合を管理し、作成・確認・回収の導線が分岐する。並行checkoutの利用者がmainへ戻る暗黙条件を知らなければ保全検査や回収が漏れる。

**推奨範囲:** 他helperと同じmain/common root resolverを使うか、非main cwdを明示拒否して唯一の管理入口を保つ。

**確信度・未検証:** high。path構成とroot resolverの静的比較。worktree作成/撤去・Git ref変更は未実施。

### MR-16 / P3: 旧固定run向けguardianがほぼ同じ2scriptとして残る

**発生条件:** 旧guardian scriptを直接CLIとして選ぶ、または監視/予算変更時に現役入口を判断する。

**根拠・呼出経路:** `scripts/dev/ai-sigma-runner.py:29–64`、`scripts/dev/ai-sigma-context-runner.py:29–64`。2scriptはdefault experiment名とstorage guard以外ほぼ同じ。旧contract fallback/quoridor-4lc.5/seed1979・固定3.5GiB RAM等を持つ。現在のsource/docs/tools/.agentsで両script名のcallerは見つからず、現役research-jobは別入口。

**既存の保護:** 現在のtask/job設計とresearch-job入口があるため、通常jobが必ず旧guardianを通るわけではない。過去rawデータや凍結比較sourceの保存とは区別する。

**根本要因:** 固定runを汎用scriptへ見せた旧経路が、撤去条件や明示的比較用途なしに二重維持される。

**影響:** 監視実装・予算の正本を選ぶ費用が増え、直接旧入口を選ぶと現在task budgetと異なる制御を使う。実害の実測はない。

**推奨範囲:** 具体的な現在比較callerが無ければ両scriptを撤去する。実利用があるなら用途と撤去条件を確認し、現役の共通job制御へ寄せる。関連する過去入力/モデル/証拠を一括削除しない。

**確信度・未検証:** high for duplication/repository callers; medium for external usage。file差分と限定caller検索。guardianを起動していない。

### MR-17 / P2: production検証が通常distをtest API付きsubpath buildへ置き換える

**発生条件:** 通常npm buildの後にverify:productionを実行し、再buildせず同じdistをpreview/配布する。

**根拠・呼出経路:** `scripts/verify-production.mjs:23–28`、`apps/web/vite.config.ts:1–6`、`apps/web/src/main.ts:694–706`。verificationはroot/subpathの順にAPP_BASEとVITE_PHASE1_E2E=1を設定して既定outDirへbuildする。vite configは検証専用outDirを指定しない。終了時のdistは最後の/quoridor/設定かつtest APIを含む。

**既存の保護:** 通常buildを改めて実行すれば正規artifactになる。通常productionのtest globals不在を検査する別smokeもあり、全配布がdebugだと判断していない。

**根本要因:** 検証fixture artifactと配布artifactが同じ出力pathを共有する。

**影響:** 検証済みと認識した既存distを配布するとbase mismatchやtest hook露出を引き継ぐ。再buildの暗黙条件が運用依存になる。

**推奨範囲:** 検証用root/subpath buildを別outDirへ置き、通常distを保護する。配布対象のbase/test-hook設定を識別・検査できるようにする。

**確信度・未検証:** high。build環境と出力設定の静的照合。build/preview/配布は未実行。

### MR-18 / P3: 手書き言語全体の限定整形を実行する入口と対象一覧が揃っていない

**発生条件:** 製品TS/CSS・Shell・native C++、または研究品質scope外の管理Pythonを変更し共通検査を使う。

**根拠・呼出経路:** `scripts/dev/check-research.py:18–50`、`package.json:16–20`、`AGENTS.md:18–22`。research品質入口の対象は指定Pythonと3 JSだけ。製品checkはRust fmt・TS型等で、製品TS/CSSやShell/native C++のformat-checkを含まない。調査した配置にはそれらを覆うformatter設定/入口を確認できなかった。

**既存の保護:** AGENTSは変更範囲に限定した全言語整形を要求し、担当者が個別に行える。Rust・研究Python/JSには設定付き入口がある。hosted CI不在そのものは現行設計上の欠陥として数えない。

**根本要因:** 変更完了の要求範囲と検証toolの対象が一致せず、担当者の個別手順に依存する。

**影響:** 各変更で整形方法と範囲を再発見する必要があり、一部言語だけ抜けても標準検査で検出されない。現在sourceがすべて未整形だという主張ではない。

**推奨範囲:** 現役手書きsourceの対象一覧と限定format-check入口を用意し、未整備言語の方式を決める。generated/vendor/凍結比較は除外し、無関係な一括整形をしない。

**確信度・未検証:** medium-high。設定とscript対象の静的調査。全baselineファイルのformatter違反検査はしていない。

### MR-19 / P3: 描画assetのfallbackで失敗原因がdiagnosticsから失われる

**発生条件:** 環境HDR/wood取得・decode・PMREM生成等で失敗する。

**根拠・呼出経路:** `apps/web/src/render/tabletop-assets.ts:39–42`、`apps/web/src/render/tabletop-assets.ts:102–108`、`apps/web/src/render/tabletop-assets.ts:149–159`。HTTP errorは原因を持つ例外になるが環境/woodのcatchは例外を保持しない。diagnosticsはerror/fallback状態・texture数・光設定だけで直近原因を返さない。

**既存の保護:** fallbackでゲームを継続でき、世代照合・timeout・GPU resource cleanupがある。利用者UIへ技術詳細を出す必要はない。

**根本要因:** 回復表示と開発診断の情報を同じ簡略statusへ落としている。

**影響:** 403/timeout/decode/GPU変換失敗を後から区別できず、asset問題の再現と環境依存調査に余計な往復が必要になる。

**推奨範囲:** asset世代ごとに有界な最新error種別/原因を開発diagnosticsへ保持する。UIは現在の簡単なfallback案内を維持し、取消済み世代のerrorと区別する。

**確信度・未検証:** high。catchとdiagnosticsの静的追跡。browser/GPU故障を注入していない。

### MR-20 / P3: 現役環境報告から参照する13枚の画面証拠が指定保存先に無い

**発生条件:** 現役報告からdesktop/mobile/角度別の完成画面を確認する。

**根拠・呼出経路:** `docs/reports/environment-presets.md:72–84`。報告は13枚の撮影を記述し、main .artifactsへの相対linkと旧environment-presets worktreeの絶対pathを示す。13指定名のis_file確認は両directoryとも0/13。限定して読んだwebapp保全manifestにそれらへのmappingは見つからなかった。

**既存の保護:** 報告の文章と既存e2eは残る。別archiveに証拠が存在する可能性は否定しない。今回完了したdocs一斉整理の件数や古いteam案内とは別の、保持中報告の参照問題。

**根本要因:** 歴史的な視覚検証証拠を一時artifact/worktree pathから参照し、現役報告への移行後の所在が明確でない。

**影響:** 報告の完成画面を読者が検査できず、文章による成功記録を視覚証拠で裏付けられない。永久消失や撮影が行われなかったとの判断ではない。

**推奨範囲:** 保存済みarchiveがあるなら13証拠の正確な所在へlinkする。無いなら利用不能を明示する。新規撮影・runtime再開は別途許可範囲で判断し、保守のためだけに自動実行しない。

**確信度・未検証:** high for referenced-path absence; medium for archive availability。指定26 pathの軽量存在確認とwebapp保全manifestの限定文字検索。全archive走査・browser起動は未実施。

### MR-21 / P2: time-limited探索でもbenchmarkがfixed_work=trueと報告する

**発生条件:** benchmarkのalpha engineでtime_msを指定し、時間上限がnode/depth上限より先に働く。

**根拠・呼出経路:** `crates/quoridor-runner/src/runtime.rs:1495–1499`、`crates/quoridor-runner/src/runtime.rs:1517–1521`。SearchLimitsはtime_msをtime_limitとして使うがreportは設定に関わらずfixed_work:true。時間制限では実際のcompleted depth/nodesが処理速度に依存し、同じ時間設定だけでは固定仕事量にならない。

**既存の保護:** 各recordにnodes/depth/secondsがあり、利用者が実仕事量の違いを読み取れる。時間制限が発火しない試行まで必ず可変仕事量だと認定しない。

**根本要因:** 固定の設定値と固定の実仕事量を同じmetadata booleanで表している。

**影響:** reportを比較入口として扱うと、違う仕事量の時間を固定仕事量として比較する誘因になる。観測済みspeedupや科学結論の誤りは未検証。

**推奨範囲:** fixed-work modeではtime_msを拒否するか、budget_kindをfixed-time/node/depthなどに区別し、実completed workと比較条件を保存する。

**確信度・未検証:** high。入力limitsとreport字段の静的照合。benchmark性能/科学効果は未測定。

### MR-22 / P3: runner helpは未実装dataset importを案内しevaluateを省く

**発生条件:** runner --helpを参照してdataset subcommandを選ぶ。

**根拠・呼出経路:** `crates/quoridor-runner/src/main.rs:44–114`、`crates/quoridor-runner/src/main.rs:158–160`。実dispatchはcache/evaluate/inspectだがhelpはimport/cache/inspectを表示する。sigma-importは別binaryにある。

**既存の保護:** unknown commandはerrorとして拒否する。既存READMEで別import入口を知っている利用者は避けられる。

**根本要因:** CLI grammarと手書きhelpが別正本で更新される。

**影響:** 標準helpから到達できない評価入口と、必ず失敗するimport案内があり、利用者がsource/docを再探索する。

**推奨範囲:** 現役subcommandとhelpを一致させ、軽量parse/help契約を検査する。必要なら共通command定義から生成する。

**確信度・未検証:** high。dispatch/helpの静的比較。CLI科学処理は未実行。

### MR-23 / P2: pagehideで不可逆disposeし、保存されたページの復帰経路が無い

**発生条件:** browserがこのページをnavigation時に保存しpagehide persisted=trueを送り、後で同じページ状態を復帰させる場合。実際のbrowser/Worker/renderer構成での保存適格性は未測定。

**根拠・呼出経路:** `apps/web/src/main.ts:691–693`、`apps/web/src/main.ts:710–715`、`apps/web/src/session/session-controller.ts:217–222`。pagehide handlerはevent.persistedを見ずにlisteners abort・input/session/review/board disposeを行い、disposed=trueへ固定する。bootstrapは初回module末尾だけで、pageshow handler/再bootstrapは現役sourceに見つからない。

**既存の保護:** 通常のページ破棄では明示cleanupが有効。保存対局からreloadして復元する入口はあるが、同じdocumentを復帰する場合の自動回復ではない。

**根本要因:** 一時的なページ退避と永久的破棄を同じdisposeイベントとして扱う。

**影響:** 条件を満たす戻る/進む復帰でUIが残ってもlistener・session・rendererは停止済みとなり、reloadまで操作できない可能性がある。現browserで必ず再現するとは判断しない。

**推奨範囲:** persisted pagehideはpauseとして扱いpageshowでresumeするか、保存復帰時に明示的再初期化する。通常破棄のresource回収を維持し、対応browserの実navigation試験を別途行う。

**確信度・未検証:** medium。pagehide/disposeとpageshow不在の静的確認。BFCache適格性・navigation/e2eは未確認。

## 保持すべき良い構成と全体判断

- ルールの正本はcoreで、Three.js/inputはRust viewと合法maskを利用する。Wasmはrules/AIを別artifactにし、同時featureをcompile errorにする。wire DTOの生成とnative/Wasm fixturesがある。
- Worker/clientはrequest・gameEpoch・revision・positionKey・generationを照合し、取消ack timeoutや再起動、session側の着手直前合法性確認を備える。単なるAPI形状検査に留まらず、stale reply、undo、restore、fault、pointer/keyboard等のe2eがある。
- Sigma研究contextのhistory/terminalは標準Gameと明示的に分かれ、NNUE/αβ/MCTS/推論queue/データ/runnerの依存は研究下層からframe固有recipeや管理scriptへ逆流していない。B0とNNUEを「重複」として一括削除する根拠はない。
- native runnerは失敗時にも予定slotをUNKNOWNで保持し、outcome/identity/admissionを新runへ保存する。backendにsilent fallbackを設けず、synthetic orchestration試験でfault・deadline・pause・join・既存出力保護を検証する構造がある。
- 資産resolver・source export・共有Beads lock・限定整形環境は正本と一時物を分ける。job controllerはbounded tailとidentityに基づく回収を実装し、応答不明の通知を成功に見せない。この外側保護はMR-03の直接cycle経路と区別する。
- `runtime.rs`（2067行）・`train.py`（948行）・`main.ts`（715行）は責務が集中するが、行数だけで分割を必須とはしない。先に所見の境界（artifact descriptor、shard batch取得、子管理、gate）を整理する方が、独立検証できる変更になる。`read_dataset`と`for_each_row`にはArrow検証の重複があるが、現時点の不一致は立証しておらず、reader共通化はデータ入口変更時に検討できる。
- Rust/品質Python/研究JSにはformatter入口がある。追加調査で、その他の現役手書き言語については整形方式の再発見コストをMR-18へ整理した。hosted CI不在自体は現行設計に反する問題として扱っていない。
- backendのshape/SHA/有限値/version拒否、NNUE通常/quantized loaderの有界read、TTのevaluator identityとhistory namespace、datasetのfamily/split拒否は、今回の追加所見にも有効な保護である。これらを一括して「検証が無い」と評価していない。

優先する修正候補はMR-01の評価入力帰属とMR-11のexport一時物によるasset破壊である。次にMR-03/MR-10の停止と記録、MR-09/MR-12の遅い設定不適合、MR-14のcache契約を、科学実行を伴わない小fixtureで補修できる範囲へ切り出せる。MR-02は大量入力の人間判断前に必要RAMと実装範囲を具体化する。MR-23は条件付きであり、対応browserの復帰確認によって優先度を見直せる。これは修正着手・実験再開の許可ではない。

## 拡張調査のcoverageと終了判断

| subsystem                                            | 読み取った主な範囲                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 限界・結果                                                                                                                                                                                                                   |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rust rules / Wasm contracts                          | `crates/quoridor-core/src/{game,position,research,profiling,lib}.rs`; `crates/quoridor-wasm/src/lib.rs`; `core independent wall legality tests; Wasm DTO/fixtures/features`                                                                                                                                                                                                                                                                                                                                                                    | Current entrypoints, rule/history/terminal ownership and selected boundary tests traced; no additional established rules bug.                                                                                                |
| NNUE / alpha-beta / MCTS / TT                        | `crates/quoridor-nnue/src/{lib,features,residual,quantized,simd}.rs`; `crates/quoridor-ai/src/{lib,research,alphabeta,sigma_mcts}.rs`                                                                                                                                                                                                                                                                                                                                                                                                          | Scalar/SIMD/delta representation, view/units, model loading, TT evaluator/history namespace and search cancellation/resource bounds reviewed statically; no numerical parity or performance execution.                       |
| Native inference / export                            | `crates/quoridor-inference/src/{lib,cuda,tensorrt}.rs`; `crates/quoridor-inference/native/{ort,aoti,tensorrt}.cpp`; `crates/quoridor-inference/build.rs`; `tools/model-export/{export,folded_sigma,verify-native}.py`                                                                                                                                                                                                                                                                                                                          | Rust/FFI ownership, shape/SHA/finite/version checks, batch state, export path and failure guards traced; vendor headers and real backend/driver behavior excluded.                                                           |
| Runner / resources / data                            | `crates/quoridor-runner/src/{main,config,resources,runtime}.rs`; `crates/quoridor-runner/src/bin/{sigma-import,teacher-qualify,nnue-diagnose}.rs`; `crates/quoridor-data/src/lib.rs`                                                                                                                                                                                                                                                                                                                                                           | Admission, paired planning, selfplay/arena queue, benchmark, engine routing, dataset finalization/cache writer and selected synthetic fault tests reviewed; not every diagnostic loop/test line audited.                     |
| Python training / evaluation / cache                 | `python/quoridor_training/{cache,common,binding,sampling,model,scaled_model,residual_model,train,cycle,plotting}.py`; `python/quoridor_training/test_{contracts,selected_target,residual_config,sampling,plotting,sharded_cache,observation}.py`                                                                                                                                                                                                                                                                                               | Config, target/schema, sampling/group weighting, native/ONNX export, checkpoint/freeze/test binding, plot artifacts and subprocess lifecycle traced. Parser-only fixture confirms MR-14; no model imports or NN.             |
| Web product / interaction / persistence              | `apps/web/src/{main,environment-presets}.ts`; `apps/web/src/session/{session-controller,review-controller}.ts`; `apps/web/src/persistence/local-state.ts`; `apps/web/src/input/input-router.ts`; `apps/web/src/render/{board-scene,board-coordinates,three-context,tabletop-assets,ambient-occlusion,environment-light}.ts`; `apps/web/src/audio/{audio-controller,audio-controls,audio-settings}.ts`; `packages/engine-bridge/src/{protocol,rules-client,ai-client,ai.worker}.ts`; `apps/web/src/test-support, product e2e and smoke scripts` | Revision/generation/epoch, stale replies/cancellation, replay/save limits, render/material disposal, pointer/keyboard, assets/audio and page lifecycle read. No actual browser, BFCache, GPU, accessibility or visual trial. |
| Task / job / storage / worktree / session operations | `scripts/dev/{research-job,research-session,research-runtime,research-storage,research-assets,research-save}.py`; `scripts/dev/{beads,beads-env,manage_worktree,project-env}.sh`; `scripts/dev/{ai-sigma-runner,ai-sigma-context-runner}.py`; `selected research-session/job/assets synthetic tests and preservation manifest references`                                                                                                                                                                                                      | Common root, process identity, bounded logs, exact descendant cleanup, durable notification and source/save boundaries reviewed; no live process/session/job/asset changes or worktree operations.                           |
| Environment / quality / dependency entrypoints       | `Cargo.toml, rust-toolchain.toml, package.json, workspace package manifests`; `scripts/dev/{check-research,setup-training,setup-rust,setup-project,verify_env,verify-rust,verify_godot_headless} entrypoints`; `.devcontainer configuration, Dockerfile, post-create/update-toolchain/storage policy`; `scripts/{verify-production,export-fresh-source} and tools/research-quality configuration`; `AGENTS.md, README.md, current development/design navigation`                                                                               | Dependency direction, source selection, format/test gate scopes and startup chains read. No environment rebuild, package installation, full lock vulnerability/version audit or external documentation lookup.               |
| Retained visual verification evidence                | `docs/reports/environment-presets.md`; `13 explicit screenshot names at main and old worktree paths`; `research-data/worktree-consolidation/1d2/webapp-preservation.json limited reference search`                                                                                                                                                                                                                                                                                                                                             | Referenced screenshot paths checked only. No full archive/asset sweep; possible archive evidence location remains unresolved.                                                                                                |

全主要subsystemの現在入口を通り、原所見の未検証点とloader・budget・schema・視点・所有・例外・asset境界を再確認した。その後の読取ではさらに別原因として根拠を出せる所見が増えなくなったため、今回の静的レビューを引き渡す。件数上限で打ち切ったものではなく、全問題を証明して出し尽くしたという意味でもない。

未調査/未検証はvendorヘッダ全体、全Git履歴・全過去raw run、checkpoint/モデル/入力bytes、generated/巨大資産、lock全依存の脆弱性/版監査、全テストの全行である。実native/GPU/ABI、数値parity、科学効果、RSS/速度、実負荷race、OS可搬性、browser/BFCache/視覚/accessibilityは確認していない。外部callerと未索引archiveの存在も未確認である。行数だけのmodule分割、意図されたSigma/標準ルール差、B0/NNUE比較、hosted CI不在など、独立した現在の問題を立証できない候補は件数に加えていない。

## 検証・引渡し

検証はソース/呼出の読取、原7所見の保存済みGit版との一致、引用sourceの現baseline byte/SHA照合、recordのJSON parse/schema・path/line整合、NN0 parser fixture、専用Prettierによる2recordの限定整形/checkである。parser fixtureは空hash map・非binary x・distance metadata不一致・manifest不変tensor変更を受理し、モデルimport一覧は空であった。実行合否やNN/GPU成功は報告しない。出力は本directoryの `report.md` と `findings.json` のみ。Rootが独立見直し・Git保存・issue受入れを行う。レビュワーはsource/docs/config/Git/indexを変更せず、引渡し時に書込STOPする。新しい修正や研究は自動開始しない。
