# 研究コードの配置と保守

Linuxネイティブを主経路とし、評価・探索・対局・推論queue・教師生成はRust、学習・解析・モデル変換はPythonを使う。具体的なビルドとrun設定は[運用手順](rust-ai.md)、学習は[学習手順](nnue-training.md)を参照する。コード正本はmain。モデル・checkpoint・入力は`research-paths.json`に示す`.worktree/assets/`の永続資産であり、コードcheckoutから分離する。移行中の使用資産は自然停止まで旧pathを保護する。旧runの参照は移動対応manifestで追跡し、原結果を書換えない。

主要ディレクトリの責務と検索の切替点は[crates](../../crates/README.md)、[tools](../../tools/README.md)、[scripts](../../scripts/README.md)、[docs](../README.md)、[保存データ](../../research-data/README.md)から選ぶ。主要構成・公開入口を移す変更では、担当ownerが対応READMEとこの案内も更新する。全階層への案内配置や新しい全資料必読・定期全体監査を義務にしない。

## 配置と依存

| 配置                                    | 責任                                                               |
| --------------------------------------- | ------------------------------------------------------------------ |
| `crates/quoridor-core`                  | ルール、局面、合法手、距離、履歴                                   |
| `crates/quoridor-nnue`                  | QF1特徴、重み、差分評価、SIMD/量子化                               |
| `crates/quoridor-ai`                    | αβとSigma MCTS、探索の取消・完了結果                               |
| `crates/quoridor-inference`             | 常駐CPU/GPU推論、共有batch queue、要求所有                         |
| `crates/quoridor-data`                  | 教師、Arrow shard、分割/露出、mmap tensor                          |
| `crates/quoridor-runner`                | native selfplay/arena/benchmark/学習cycleと回収                    |
| `crates/quoridor-wasm`                  | 製品用Wasm境界。同じRust評価・探索を使用                           |
| `python/quoridor_training`              | モデル、設定、尺度、指標、学習曲線、freeze/test                    |
| `tools/model-export`                    | ONNX/AOTI/TensorRTへのオフライン変換                               |
| `tools/research-session`・`scripts/dev` | 明示thread宛のタスク通信、非同期jobの回収・完了通知、Git保存と容量 |
| `tools/research-quality`                | Node用Prettierと共通PythonのRuff・保守テスト                       |

NodeはWeb/Vite/TypeScript、Wasm製品ビルド・検証、品質とソース書き出しに必要。研究の対局・探索・推論・生成をNodeへ委譲しない。旧Node実装、互換shim、実験別コピー、旧Python学習recipe、旧実装との比較テストは削除済み。移行前コードはGit `54a294a`、[撤去manifest](../../research-data/ai-sigma/retired-code-cleanup/removed-source.json.gz)と[検証](../../research-data/ai-sigma/retired-code-cleanup/verification.json)で追跡する。[AGENTS.md](../../AGENTS.md)の方針に従い、保守コストを優先し、互換性維持を目的とした旧経路は保持しない。実施中・具体的に予定した直接比較に必要な旧版だけは比較専用に保持し、対象・用途・撤去条件を明示する。比較時にGitから復元する手順は挟まず、終了後に不要分を削除する。

Rustの共通crateから過去frameのコードや管理scriptを呼ばない。PythonはRustが生成・検証したtensor又は66B canonical geometryを読み、学習loop内では限定batchのQF1特徴を展開する。ルール・距離・盤面の合法性を学習loopで再計算しない。モデル定義・設定・尺度は同packageに置き、`sys.path`で旧ツールを取り込まない。学習済み重みと凍結データはコード移行で書き換えない。

各保証には一つの検証境界を定める。詳細なsource・履歴・teacherの対応はcache変換・公開で検証し、学習は固定binaryと必要な小さいconfig・identity・件数・family/split情報を消費する。下流でsource全体を再検証する追加処理には、既存境界では防げない具体的な失敗条件を示す。受渡しの精度・schema・単位は正本を一つにし、同じteacherをJSON数値とFP32で繰り返し解釈・比較しない。変更されたteacher bitsの拒否は維持し、数値許容差で代用しない。新しい接続処理はsource/mock検査だけで完了とせず、影響する実際の生成・変換・binary読込の小さいend-to-end経路を一度確認する。検証の追加が実行中の凍結入力・codeを変更したり、成功した科学runの再実行を要求したりしないようにする。

Rustのbuild依存管理はCargo/rustcを正本とする。同じbuildを認定する独立したsource一覧、alias、埋込みsourceコピー、第二の依存graphは維持しない。必要なfile依存記録は所有するBUILDの標準tool出力から得る。既存build記録には実Git revisionと関連する未commit差分、Cargo.lock・features・profile・target・実command、必要なtool版、artifact identityと実check結果を残し、Cargo.tomlだけを完全なfile一覧とみなさない。外部model/dataと実際に読み込むcaller/libraryは、それぞれの所有境界で束縛する。compiler/test/lintの成功は棋力結果ではなく、記録処理の失敗はmodel失敗ではない。変更していない成功checkは元の適用範囲で再用し、必要な変更checkや通常のdebug確認を行政的な再実行禁止と混同しない。

## 共通計測入口と実行記録

人間は、Search/evaluator/sessionと既存caller/job・標準perfを再用する一つの計測入口を選択した。差し替えるのは計測operationと必要な準備/reset/後始末だけで、plugin/registry/frameworkは追加しない。入力・対象・探索設定・件数/順序/seed・cold/warm寿命・warmup・perf設定はconfig/scheduleへ置く。実験番号、固定SHA、20/80/36/6やsampling値を共通sourceの拒否条件にしない。直接比較中の376A/Bはconfigで対象を選び、比較終了後に不要な専用入口/schema/CLI/shim/testを撤去する。現役入口は`quoridor-runner measure`（Cargo feature `measurement`）へ統合した。旧360/376/349専用入口・schema・生成/資格判定は撤去した。対象A/B・入力順・件数・session・perfは設定から渡す。Pythonの既存限定検証を元scopeで受け入れ、統合時に見つけたteardown session名と途切れたjournal末尾の記録を修正した。新しいRust3定義は実PASSした。続くClippyのtest-module配置指摘はmoduleを末尾へ移すだけで修正し、成功した3定義のbodyを変えず再実行していない。必要なClippy/release・真正artifactとraw-profiler所有境界を通常修復で確認し、349の全36 callsは実COMPLETEになった。元のsampled CPU entry／引数／permission拒否、RAWとUNKNOWN・mixed-image制約は保持する。終了済み36を再実行せず、結果の解釈は既存findingsを参照する。

保存の基本単位は、実際に使った設定snapshotと結果の一組である。code版・共有model/input参照・実設定/環境・実測/件数/完了未完了/errorをmetadataへまとめ、perf RAW等は結果から参照する。別のsource一覧・資格/acceptance/certification/control台帳をrunの必須成果物にしない。job/processの一時cleanup状態は認定書ではない。予定36で実施24なら24と未完了12を記録し、計画差だけで停止・全結果拒否・別認定をしない。比較条件の差は解釈に明記し、不正入力/モデル読込errorや取消/未完了を成功へ変えない。旧科学RAW/FAILED・actual identity/ownership/cleanupを保持する。

## 品質確認

arena/decisionsと保存解析の現役ownerは既存plan/configを消費し、family/slot/matchup/engine順序・model/history・depth/time/reserve・ordering設定と予定分母を照合する。解析seed/resamples/central intervalは選択configから取り、engine IDをSigma/Alphaの意味へ固定しない。選択authorityは実親job/Run/settings又は既存issued admissionで、二つの可変fileが相互一致するだけでは代用できない。元native publicationは元Build/imageに束縛したまま、解析toolの版と混同しない。詳細と未対応backend/modeは[runner手順](../../crates/quoridor-runner/README.md#configured-research-plans-and-saved-analysis)を参照する。

generation-onlyの固定plan/hash・件数は、その明示issued generation subjectの入口に残る。generic arena解析の128/768/三engine等とは別のcallerで、既承認生成や381の選択をarena保守だけで変更しない。保存解析/NN0 metadata試験の成功はmodel/backend/実棋力資格ではない。

```bash
source scripts/dev/project-env.sh
bash scripts/dev/project-env.sh python scripts/dev/check-research.py --syntax-only
bash scripts/dev/project-env.sh python scripts/dev/check-research.py
bash scripts/dev/project-env.sh python scripts/dev/check-research.py --format
npm run check:native
# 製品とnative双方を変更した場合
npm run check:all
```

軽量チェックはPython AST、Node構文、限定整形、現役NN0学習/cache/freeze・回収・保存・export・task session clientの契約を明示suiteで確認する。Torch/ORTの読み込み、学習、対局、非同期job起動はしない。nativeの回収・探索・特徴・重みテストはCargoで、実Wasmの評価/取消は[運用手順](rust-ai.md)で確認する。科学実行の許可と構文検査を混同しない。

`npm run check`は製品core/AI/WasmとWeb/DTO/fixture/境界/audio/renderを、`npm run check:native`はnative研究crateを選ぶ。`check:all`は製品・native・軽量研究の統合入口とする。通常のproduction distを検証用buildで上書きせず、`verify:production`は専用outDirを使う。

共有Cargo targetでは、worktreeの凍結ソースを旧mtime付きで復元すると、別版のrlibをCargoが`fresh`と判定する場合がある。現在のsource SHAを記録しただけでは使用されたcache payloadの版を証明しない。唯一Cargo writerの次entryで、担当source・compiler/flags・lock・実使用artifactを束縛する。鮮度修復が必要なら、読者停止後にSHA確認済みの名前を指定した担当sourceだけのmtimeを更新し、必要scopeを再compileして新artifactとlinker/TMP費を記録する。数学・ソースbyte・凍結private ELF・失敗原記録を維持し、Cargo cleanやtarget全量走査・cache削除を修復の代用にしない。

Python品質・学習・管理依存は同じルートlockと共通環境を使う。環境変更は既reader停止後の明示setupだけが行う。NodeのPrettierは既存Node lockを使う。

```bash
npm ci --prefix tools/research-quality
bash scripts/dev/setup-project.sh --python-only
```

## 保存と再構成

通常のsource/docs変更・限定test・incremental build・実行artifact copy・reviewは保存予算なしで実装/検証し、終了後に対象の実量を一度確認する。異常な大きさや残存TMP/log/copy、実空き不足のみ限定対応する。具体的なbulk生成/取得/checkpoint/RAW/cache仕事だけ事前保存予算を設定し、歴史subcap/予約一致を通常入口へ復活させない。CPU/RAM/VRAM・50GB・科学許可・所有/reader STOP・artifact identityとcleanupは維持する。

Gitにはコード・設定・必要な実験検証データを保存する。実行出力、モデル、build、依存cacheは[保存方針](../../.devcontainer/storage-policy.md)の領域に置く。利用中の入力や未追跡資産をコード整理に巻き込まない。保存・復元・参照終了を確認してから展開重複を整理する。過去結果の再現に必要な旧ソースは記録Git版から復元する。

`node scripts/export-fresh-source.mjs --scope research --destination <新出力先> --max-bytes 67108864`は現役crate、Python、管理・品質ツールと文書を書き出す。モデル・科学データ・runtime・一時sessionは含まない。限定集合は`--paths-file`で指定できる。既存出力やindexは上書きしない。

ONNX Runtime 1.30.0はtelemetry初期化時に`:memory:.ses`を生成する。`project-env.sh`とDevContainer設定は`ORT_DISABLE_TELEMETRY=1`を指定し、runner・学習package・環境診断もORT読み込み前に無効化する。任意の外部PythonからORTを直接読み込む場合も、この環境変数を先に設定する。既存コンテナの新設定は`source scripts/dev/project-env.sh`で適用できる。

### 永続資産と旧pathの追跡

`research-paths.json`のmodels/checkpoints/inputsは`.worktree/assets/`のカテゴリを指す。コードcheckoutを保存先にしない。現在の資産解決は`bash scripts/dev/project-env.sh python scripts/dev/research-assets.py --kind models --name ai-sigma/reference/sigma-pcr250/best.onnx`。内容確認を伴う場合だけ`--sha256`を付ける。旧payloadの絶対pathは`--legacy-path <original-path>`で移動対応manifestへ照合できる。未対応・欠落・範囲外参照・SHA不一致はエラーとし、旧worktreeへのfallbackやsymlinkを作らない。

旧weight-manifestは元の絶対pathのままmain Gitへ保持する。現在のNNUE descriptorは`--kind models --name legacy/frame18-native-connection/manifest.json`で解決し、相対weights参照だけを移行先へ更新した。重み・特徴・scale・教師ラベル・split・旧runの条件は変更していない。新runは現在の解決済path/SHAを自身の設定へbindし、旧run原記録を上書きしない。既入力の移動は自然停止・子回収とbyte確認後に同volume renameで行う。資産移動・チェックは学習/推論/対局を起動しない。

軽量検証は`bash scripts/dev/project-env.sh python -B scripts/dev/test_research_assets.py`。資産解決、欠落、path traversal、symlink範囲外、旧payloadのSHA/size変化を合成fixtureで確認する。旧checkoutの撤去では未保存情報のGit/圧縮保存と復元を確認し、registered checkoutは`manage_worktree.sh remove`、Git操作窓は単一統合ownerと合わせる。保全・移動対応は`research-data/ai-sigma/1d2-worktree-consolidation/`、製品固有証拠は`research-data/worktree-consolidation/1d2/`へ分けて保存する。原pathとSHA・復元参照はこの保存先のmanifestで追跡し、終了済み報告は[文書索引](../README.md#過去文書と証拠を探す)からGit版を特定する。

## 設定を使うarena／計測の有限実行

### 通常研究の探索標準（412、2026-10-15）

人間が選択した今後の通常研究探索・棋力評価の基本設定は **LMR ON / `depth_rank`**。これは研究上の選択であり、一般棋力の優越を確定したという意味ではない。比較対照の明示LMR OFF / `fixed_one`はそのまま使える。減深tableの係数・保護・full-depth scout確認/PVSは408の既存方式を変えない。

既存 `research-lifecycle.py::comparison_conditions(common)` が通常研究の省略を解決し、`lmr_values`省略ならONだけ、`lmr_method`省略なら`depth_rank`を条件へ明示する。`apply_comparison_cost` / `apply_comparison_arena` はその条件を同じ既存measurement/engine設定fieldへ書く。明示`lmr_values`やmethodは保持する。live preparation helperが標準の解決ownerであり、artifactの古いrecipeや別preset registryを正本にしない。

この研究準備と、汎用設定reader・製品・実generatorのenable既定は別である。直接measurement/Engine JSONやSearchSessionでenableを省略してもOFFのまま。method省略はAIのtyped `LmrMethod::default()` = `DepthRank`へ揃えるが、method選択だけではONにならない。measurementのmethod null/未知名/型違い拒否、Engineの既存Optionとarena planの型規則を変えない。typed method・namespace/reset正本はAIだけで、Pythonは設定名を解決しID/suffixを再構築しない。既存`configs/arena/distance-control-*`は明示source SHAを持つ調整用D/D例であり、この標準を理由に凍結値をretargetしない。

各runは解決した`lmr` / `lmr_method`、実methodとnamespace、実image/Build、入力、費用・結果・UNKNOWNを保存する。410/411の発行済み比較は元LMR OFF/imageのまま保持し、この既定更新を混入しない。412追加対局も真正408の同一imageを用い、A固定1手/B深さ順位を両方明示するため、新しいdefault imageへ合わせた再buildや元成功局の再演を要求しない。旧400/402/408の有限判断は当時の設定として保持する。

製品・実generator・paused mixed/learner全prep/pipelineと323、models/weights/seals/oldfits96の変更や新科学実行を、この標準から許可しない。

モデル・book・数量・順序・範囲・clock／探索limitは実設定へ置く。arenaの既承認範囲・入力と実Experimentの対応を既存入口で確認し、有限sequenceはその設定からoperationを導出する。個別pairの手書きready admissionやLLM受付を前提にしない。共通`measure`は対象profile・入力schedule・cold/warm session・任意の標準perf設定を読み、実際のcalls／completion／error／UNKNOWNを結果へ記録する。実験番号・固定数量・literal SHAとの完全一致を共通sourceの認定gateへ戻さない。真正artifact／model／input／caller identityとCPU/RAM・取消・exact cleanupは維持し、予定との差は実施数と未完了数で説明する。

既承認のarena suffixとPerfの残りは、一つの有限code-driven jobで既存entry/guardianを直列に合成する方針へ改めた。実設定・範囲・順序を一度採用し、成功したpair/pass間のLLM準備・手書きadmission・個別配送を撤去する。pairの統計単位・method/models/math/clock・actual identity/cleanupは保ち、unexpected error/pauseで停止して記録する。旧frozen helpers/RAW/FAILEDは原記録であり、現役の互換・起動gateにしない。

## 設定可能なoutcome生成／混合学習

入力準備は `quoridor-runner teacher-pilot --prepare-inputs SETTINGS --input-sha256 SHA` を一度実行し、既存`teacher_pilot`／depth6生成へ実global schedule・family partition・batch sliceを渡す。通常RUNを `sequence` の `settings.runs` で設定順に合成し、childwait・結果・正常finalization・cleanup後に次へ進む。現在は明示的 `finalizers=[]` のRUNだけを扱い、missing/null/nonemptyを所有前に拒否する。変換は`terminal-cache --input STREAM [--input STREAM ...] --output NEW_OUTPUT`を使う。追加の実lineage参照が必要な場合だけ`--input-binding PATH --binding-sha256 SHA`を併用する。converterが系列漏れ・実terminal outcome・UNKNOWN・chronology・binary teacher bitsを確認し、v3 compact cacheと実ordered source参照を公開する。`root_value_policy="outcome_only"`はzSTMを教師とし、旧raw探索値の範囲でnear-goalを除外しない。元raw FP32、source eligibility、実threefold0とUNKNOWNは区別して保持する。

学習は通常の`train --cache PATH --output PATH --config CONFIG`で`experiment.study="mixed-outcome"`／`training.target="z"`を選ぶ。`mixture`に実T-family view cap、source別batch行数・reflection probability/seed、露出上限・public sampling/diagnostic seed、accepted public membership/custody参照、public-V selector、output limitを置く。training.stepsは有限最大値であり、実露出からのhorizonと実attempted／returned counter・別T/V curves・INITIAL/BEST/LASTを保存する。共有corpus/modelをrunごとにコピーせず、別のplan／資格／admission台帳を必須成果物にしない。381はsource/software準備であり、新しい生成数・fit・BEST条件・容量停止方針の未選択値を科学実行へ自動採用しない。通常converter/runner BUILD、必要なaffected assertions・Clippy/release、重要なlabel/split/mixtureとRUN義務境界の限定確認は完了した。accepted converter→実common_cache_config／TerminalCorpusの小さいsynthetic接続も実PASSであり、actual model forward/fitは0である。実新データのGPU fit・新weights確認や科学実行は別の未実行工程である。

### 比較条件とコード配置の正本（403）

評価器（対応model・identity）、Control／Cheapの静的採点、LMR OFF／ONだけを比較要因とする。TT1048576・TT利用・PVS・rules・full history・入力、operation内の深さ／node上限・時計／reserve・物理配置は今回の共通条件から解決する。計測の固定depth/nodeと対局の100ms receipt／5ms reserve／node safety1Mは異なる意味を保ち、それぞれの条件内で揃える。最終prepared metadataに実設定の小さい条件表を保存し、model／namespace導出、runID／出力pathを比較要因と混同しない。旧400は当時profileと非対称TT容量の有限結果であり、評価器演算単体・静的整数項単独の効果ではない。

配置は既存crate内で責務を分ける。AIのalphabetaがsession設定・method・探索、move_orderingがrank/keyと準備・整列、二scorerが異なる採点数学、static_geometryが同じ盤面算術だけを所有する。runnerのmeasurement／arena／runtimeはoperation固有の拒否・時計・回収を保持し、typed profile／method／factoryの正本をAIから呼ぶ。旧new_for_ordering_assessmentの互換aliasは残さない。

再利用する条件列生成と明示field解決は既存scripts/dev/research-lifecycle.pyの準備関数へ置き、namespace文字列をPythonで再合成しない。今回一度のprepare-cost96.py／prepare-arena128.pyと有限recipe値はartifactのrun記録とし、再利用処理の実装コピーを残さない。nativeは省略overlayではなく解決済みJSONを読む。実行設定snapshot＋結果が記録単位で、別の逐次認定台帳・runtime継承設定・generic merge・registry・毎run reviewは増やさない。live outputは専用owner、Git保存する設定・結果はresearch-data、models／inputs／checkpointsはresearch-paths.jsonの永続assetsに保持する。旧path／SHA、固有RAW・モデルの移動／複製は不要で、全repo移動を比較gateにしない。

今回選択した共通準備・typed method/constructor・採点幾何・準備入口の配置は、限定Rust14確認／NN0新1と必要compile/Clippy/release・関連source確認を経て採用した。整理後96探索／128探索的対局の設定と結果・深さ分布・UNKNOWN・費の範囲は[保存receipt](../../research-data/ai-sigma/shared-signed-ordering402/receipt.json)に保持する。実imageはsource93cbcd70の凍結版であり、後続の文書commitに合わせた再buildは行わない。全repoの重複不存在を認定したものではなく、別算法やoperation固有の拒否・時計・回収はそれぞれの責務に残す。
