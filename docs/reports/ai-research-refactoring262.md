# 研究コードの保守構成への移行 / quoridor-4lc.262.1

2026-10-05。mainへの研究統合後、診断259の全テーマを対象に、今後の変更・検査・保存・再現・運用費を減らす構成を実装した。Stewardと短期担当が実装・NN0検証を停止してRootへ引き渡す。Rootの最終レビュー・通常indexでのcommitは別の受入れ段階であり、科学成果や研究再開を認定する報告ではない。

基準統合は `1811919718a1837b376a148291e0d43c3e9dd683`。途中、Root263がGit履歴修復を引き取り、最新treeと作業sourceを保持したHEAD `a0c43016e0a10e252fd06405f6cf893f6c434a30`へ移行した旨を受領した。Stewardは履歴修復・push調査を打ち切り、index/commit/refsを操作していない。旧原版はRootの保全refと各runの版を参照し、科学データの変更や旧成果の再計算を行っていない。

## 到達構成と実caller

[研究コードの保守案内](../development/ai-research-code.md)に配置図、依存方向、入口、明示設定、環境復元、保存・容量操作を記載した。mainをコード・文書・Git保存データの正本とし、旧worktreeのcodeを恒常mirrorしない。モデル・入力・共有envは既pathを保護し、`research-paths.json`でコードcheckoutと分けた。

| 境界 | 実装と利用先 |
| --- | --- |
| ルール/history/terminal | `tools/ai-sigma-native/rules.cjs`と`rules/`。State VMを分離し、MCTSを必要としない利用者から参照できる |
| 特徴・NNUE・探索 | `features.cjs`、`weights.cjs`、`nnue.cjs`、`leaf.cjs`、`search.cjs`。frame/fixturesへ逆依存しないQF1・float32 codec/差分・αβ。frame20 arenaの3callerは新探索境界へ移行 |
| native MCTS/IPC | `reference.cjs`・`mcts/`・`controller.cjs`・`mcts-worker.cjs`・`inference/ort.py`。現manygame worker/export/probeがcanonical nativeを利用 |
| Rust bridge | `tools/ai-sigma-native/bridge/`。旧private depsの同一7sourceコピーへ依存せず、main `crates/quoridor-core`/`quoridor-ai`を参照。明示cache/targetdir、offline/locked/jobs1、共有JSON-line Pipeへ実接続 |
| 多game生成 | `ai-sigma-common/generation/`と`process/`へ識別、batch、独立gamepool、教師schema、IPC、所有回収・run制御を分離。既manygame caller/shimが共通実装を使用し、新`generate-run.cjs`は明示configで利用 |
| 学習 | `nnue-training/qf1.py`、`dataset.py`、`exposure.py`、`metadata.py`、`learner.py`、`scaled_model.py`。`run.sh`は汎用learnerへ。frame14固定split/maskのrecipeと入力APIを分離し、旧`train.py`は凍結原版を保護 |
| 検査・保存 | `check-research.py`、`research-save.py`、`research-storage.py`、安全な`export-fresh-source.mjs`。構文/限定整形/NN0契約、通常index保存、inode会計、sourceのみの専有export |

新arenaはrun ID/issue/owner、合法openingと全予定slot、明示budget/NN/node/depth上限、transport上限、pause・Beads・終了/回収余裕・CPU/RAM/output guardを先に検証する。未知slot・空選択を成功にせず、既存出力をtruncateしない。初期化失敗を含むfinallyで所有childを回収し、必要な終了不成立もtyped記録にする。

生成の教師K/温度・探索量、model/hash/env、worker/game/CPU割当、provider・実batch、RAM/VRAM/保存/期限はrun configへ分離した。過去500msや旧issue時計を将来APIの必須条件へ埋め込まない。既GPU providerの固定graph/モデル条件は凍結recipeで保持し、新入口はprovider commandを注入する。この保守移行で実GPU/batch parityを認定しない。

## 診断7テーマの処置

| テーマ | 解消済み・今回実施 | 意図した保持と再検討条件 |
| --- | --- | --- |
| index/HEAD/WT保存 | 261の通常index統合を継承。新save helperは明示file集合・Git owner・writer停止・Beads担当/no pause・既stage拒否・forecastを確認し、通常add/commitする。private-index HEAD-only保存を標準から外した | Rootだけが今回commitする。失敗stageを自動resetしない。旧保存recipeは原Gitへ。履歴不正tree/push問題はRoot263担当でStewardが重複調査しない |
| 二重正本/worktree | main統合正本、旧WTは凍結参照/資産、恒常mirror停止をREADME/AGENTS/team設計/storage policy/実行記録へ整合。registryのcode root/cwdとclient dispatchをmainへ | 旧WT volume・未追跡・モデル・入力・共有Gitは残す。入力参照の移行と復元が成立するまで消さない |
| 現役依存/設定 | 上記native/common/training/bridge境界へ実callerを移行。frame設定・fixture読取・AST改変を汎用APIから除き、通信/所有/終了制御を明示 | Rust/CJSの科学算術と教師規則を保持。新言語・探索法・評価条件への変更は科学契約へ切り分ける |
| 用途別重複 | 共通保守するbatch/gamepool/schema/pipe/identityの旧local実装を互換shimへ一本化。Rust copied depsを現役依存から除外 | 独立checkerと凍結oracleは統合しない。旧145実験を一括改名・移動しない。shimは既caller撤去と原Git/入力復元確認後に除去する条件をREADMEへ記載 |
| 可読性/検査/文書 | 限定したPrettier3.6.2/Ruff0.13.1を専用lock/envに固定、現役CJS/Pythonを整形・責務分割。1入口の構文/依存/NN0検査、配置図・入口・recipe・再現commandを整備 | vendor/raw/全旧recipeを一括整形しない。製品全build・NN・学習を検査から暗黙起動しない |
| 保存/展開/build | Gitデータとlive/extraction/build/tempを明確化。source exportは必須新destination・scope/path集合・byte forecast、既存dest/科学data/temp/symlink拒否、現在WT hashのmanifestを実装 | 旧保存archive・必要モデル/env・未知展開は削除しない。新bridge targetは再構成可能だが次の利用費を下げるため保持し、ignored実量として計上 |
| 共有cache容量帰属 | 明示root/category/reservationの容量helperで同dev/inode/overlapを一度だけ計上、logical/allocated/unused/peak/unknownを分離。小fixtureで重複・未知・予約の算術を確認 | 限定観測のinode allocation約14.8GBは12GiB内admissionを支持しない。reflink物理共有/対象外帰属/有効予約に不明が残り、unknownを空きにしない。新science前に契約対象を現在観測する |

配置整合の公式idle resumeは同saved/model/effortで受理されたが、4roleの応答・thread/readに旧cwdが残った。恒久cwdの実変更を支持しない。新clientはregistry `code_cwd`を次idle taskの公式turn/startへ明示し、active steerではcwd変更を行わずraceを拒否する。mockでこの配送条件を確認した。実taskのcwdと役割効果は次の許可taskで確認するため、確認だけの新研究turnを作っていない。developer本文readbackも非対応で、保存hash/受理と実効果を分けた。

## 整理したものと保持したもの

今回所有の品質依存取得cache `.artifacts/refactor262/dependencies/uv`だけを、使用process無し・Ruff固定版と復元手順・installed binary hashの前後一致を確認して整理した。logical filebytes38,888,745B、cache側inode allocation38,907,904B、整理後このpathは0B。hardlink/reflink共有があるため物理解放量は不明で、親予約の減額や未知保持の帳消しには使わない。記録は `cleanup-quality-cache.json`。

必要な専用quality env/node_modulesと新bridge build target（約24.5MiB）は保守検査の再利用費を減らすため保持した。旧共有training/team env・uv cache・モデル・科学data・展開・`:memory:.ses`は保持した。大archiveの展開や依存削除を実施していない。旧展開の一括整理は現読者/所有/必要入力の判別をまだ満たさず、次に具体的なunused scopeが判別できた時点の担当配分へ引き渡す。ファイル数削減を保守成果の代用にしない。

## 検証と失敗の保持

最終 `taskset -c 0 python3 scripts/dev/check-research.py` はexit0。49 JS構文・17 Python AST、限定Prettier/Ruff、共通moduleから過去frameへの逆依存検査がPASS。

| 検証 | 最終結果と範囲 |
| --- | --- |
| native | 39/39。合法手順/float32入力/history/terminal、STM特徴・cache、codec/差分parent保全、完成済みdepth/cap/cancel、manifest hash/実size、arena初期化・output・予定分母・NNcounter、正owned取消回収、transport caps/EOF/EPIPE/late/parse時計/stdio-close |
| 学習入力/learner | 8+6 PASS。QF1/schema/game split/mask/入力hash・dry-run/source binding。Torch import/forward0。初期段階の旧互換も別途有限確認 |
| 生成共通 | 18/18。partial batch帰属、cancel/drain、sample cap、合法教師schema、config/env/hash、IPC/owned close/VRAM parser・pause/期限。実NN/GPU無し |
| 保存/容量 | 14/14。合成temp Gitだけで通常index保存/refusal/unknown/同inode予約算術。project index/HEAD操作0 |
| client | 11/11。main/managed cwd、凍結WT拒否、idle explicit cwd/active preserve/race、pause/dispatch/応答不明。新実科学turn無し |
| source export | 3/3。物理source/hash、新dest専有、既dest保護、science/temp/symlink/oversize refusal |
| arena clock fixture | 6PASS、samples0。late/stale/incomplete/parse-validation超過/EOF/回収 |
| Rust bridge | offline/locked/jobs1で5NN0契約PASS、実binaryと共通Pipe JSON-line fixture/exit0 PASS。旧3sourceはrustfmt正規化後同bytes、Cargo.lock同bytes、依存取得0 |
| 独立レビュー | 初回8所見と最終3所見を保存し、終了回収/出力保全/予定分母/manifest/NNcounter/stdio有界化等を修正。最終少数readの重大残0。科学動作は未認定 |

途中の不成立も消していない。Rust標準cacheのryu不足は取得せず既cacheを再用、fixtureの不正prefix/terminalとformatter比較方法を補正し科学sourceを変更しなかった。transport mockのstdin閉鎖/小chunk burstが検査目的を再現しなかったためfixtureだけを修正した。新arena configと旧fixtureのCONFIG_issue差、生成provenance検査の管理affinity差、client試験をsystem Pythonで呼んだwebsockets不足は、fixture/検査入口の現在契約へ修正した。最終正常runと分けて `verification.json` に要点を保存した。

実モデルforward・NN・学習・対局・GPU・研究scheduler起動0。検査は最大2logicalの枠でCPU0単1を基本に、既worker mockのCPU1窓と並行して上限2内。framework importを必要とする科学commandは実行しない。Rustも既依存のoffline NN0契約のみ。資源/新保存のforecastは引渡しreceiptを参照し、旧累積保持量をresetしない。

## 引渡しと次の利用

全source writer・短期子を停止し、Rootへ明示変更pathとsource hash、検証結果、Git未commit一覧を引き渡す。Beads262.1と子はRoot受入れ前のin_progressを維持し、backup syncする。Rootが通常indexで明示pathを保存・最終受入れ後closeする。保護対象`:memory:.ses`を変更集合に入れない。

次の許可された研究は、main clientのexplicit cwd、canonical native/shared generation、generic learnerと明示run configを利用できる。NN0の実IPC・bridge binary・learner dry-runでこの利用経路を確かめたが、実科学の品質・速度・棋力改善は次の契約で評価する。恒久cwdの実読取と現在容量admissionは未確認を明示したまま渡す。これらを旧科学成功や未来停止保証へ置換しない。

## Root最終受入れ

Root側でも `taskset -c 0 python3 scripts/dev/check-research.py` がexit0となり、Stewardの停止引渡し123ファイルのSHA/bytes一致を確認した。独立レビューの修正記録と、現役caller・保存/配置/品質の境界を確認し、保守変更を受け入れた。通常indexで指定124pathだけを保存する。Rootレビューでは利用案内の過去版参照を修復済み `a0c43016e0a10e252fd06405f6cf893f6c434a30` に合わせ、旧IDは263の対応表から引けるようにした。科学データ・原recipe・教師条件には追加変更していない。

実行cwdの確認と共有容量の帰属は上記の未確認事項として残す。新科学の前に担当契約の資源と実行場所を確認するが、保守実装の未完了や研究再開とは扱わない。今回のsource・短期検査は停止し、scheduler/研究は停止したまま。コミットのIDとタスク完了はBeadsから参照する。
