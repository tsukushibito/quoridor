# Sigma自律研究・継続枠 2026-10-01

契約版3（ユーザー85/85.1の実行・記録規約を本文適用）。目標quoridor-4lc。統括01a0f31b-3409-75f2-a30e-453a50484f94。根拠はユーザーの明示継続/詳細委任（root入力01a0f2e9-357d-7ef3-a2fe-b16f80accda5）。開始2026-10-01T09:03:36.459834+00:00、終了2026-10-02T01:00:00Z（2026-10-02 10:00 JST）。本書は新しい実行枠であり、旧目標契約版2の初期04:00終了/未達/過去逸脱を保持する。旧文書・旧preregister・成績は変更しない。目標/比較A/通常製品規約維持/独立検証/権限は旧目標契約を継承する。

固定Sigmaと同計算資源・思考時間でnative/localおよびbrowserの非劣性を実測する。旧32局m8のnative.5625/browser.1875と両下限未達を保持。今回の新比較はcode/model/config/pool/T/g/m/CI/停止/責任分類を結果前に別事前登録し、旧結果へ後付け条件変更/標本統合をしない。未使用m10計画は参考として残すが、実入口/共通時計/資源gateと新deadlineを独立freezeするまで対局禁止。

予算はCPU全計4logical、RAM全計8GiB、LLM最大3（統括と新supervisorを含む）、正式CPU比較はCPU2単logical/推論threads1/GPU推論0/他の重い研究job停止。GPU研究は旧上限6GiB・1job30分・累積2h以内を保持し、今回は別配分前GPU/学習0。成果/依存は旧枠から累積12GiBを維持、リセット/12GiB追加ではない。旧限定保守課金6,588,000,723B・条件付き残6,296,901,165Bを開始時再確認する。初回新規予約: entry2GiB（guard1.75GiB）、steward128MiB、監督32MiB、統括文書32MiB。未配分は基準再確認後に統括が同12GiB内で配分。副次cache/途中展開/一時profileも計上。既存共有training/cacheは読取のみ、削除はこの枠が所有する再生成物だけを証拠保持の上で別に判断。

既存五役saved sessionを維持、新supervisorは既存App Serverに永続登録して観測専用で追加。App Server/toolchain再起動やモデル/effort変更をしない。新有料API/クラウド/第三者オンライン対局なし。主checkout製品/UI/描画/M2への統合、push、公開は対象外。研究worktreecodex/ai-sigmaでは研究コードのローカルGit管理を許可する。コード版/runと必要な差分・入力参照を記録し、新copyや全入力hashを一律必須にしない。スケジューラーは主checkoutのpush済み操作入口を利用し、運用role定義/registry/専用configだけを用意する。

監督issuequoridor-4lc.40、20分周期/1turn180秒（新job120秒で停止し報告へ）、終了2026-10-02 00:55UTC、観測のみ。globalは3だがschedulerの起動閾値max_active_sessions=2として統括報告の起動1枠を残す。枠使用中はskipしsteerしない。変化なしは保存のみで静かに終了、意味ある停滞/失敗/期限資源/完了時にだけ統括へreportする。監督が設定や課題配分を変更しない。pause/終了はownedturnだけinterrupt確認し、外部jobは各ownerが回収する。dispatcherや監督の停止だけでNN停止を認定しない。

初回はquoridor-4lc.38stewardがscheduler準備/実運用/容量/資源台帳、quoridor-4lc.39experimentがORT入口・復旧gateを担当。途中から競合A共通tract/B分離ORT/C B0とH1backend/H2探索/H3時計・checkpoint/H4標本を更新し、通常判断は統括が実依頼する。別の選択が有望ならこの枠内で契約を作り替えるが、結果を見た正式判定緩和は行わない。

終了: 目標達成、ユーザーpause、上限/guard/異常、2026-10-02 01:00UTC。2026-10-02 00:50UTCまでに新重jobを止め、終了処理を確保する。全ownerはPID/starttick/command/hash/exit/資源/失敗/stopを先保存、報告は簡潔に詳細JSONへリンク。達成なら独立根拠で目標close、未達なら次の継続/停止理由を記録。予算を自動延長しない。各実行deadlineは本枠以下。担当へ実送信/受領をBeadsとdispatchに記録する。

継続委任は目標へ向けて継続する指示である。未達の場合は本枠終了前に統括が次枠の必要性/予算/検証を判断し、ユーザーへ通常詳細の再承認を求めず別契約として具体化できる。同一枠の期限や累積12GiBを黙って拡張しない。

## 期限変更根拠（版2で受領、版3でも期限不変）

2026-10-01、操作元root 01a0f2e9-357d-7ef3-a2fe-b16f80accda5からユーザー明示指示を受領。「明日午前10:00」は2026-10-02T10:00:00+09:00 = 2026-10-02T01:00:00Z。開始時刻は維持し、旧継続枠終了2026-10-01T17:00:00Zから終了時刻だけ変更する。重い処理停止00:50UTC（09:50JST）、監督運用停止00:55UTC（09:55JST）、monitor回収00:58UTC、枠終了01:00UTC（10:00JST）。目標達成・pause・guard停止条件と時間以外のCPU/RAM/LLM/累積容量・許可範囲・独立検証は変更しない。

旧版SHA859bb777836cc0683e1ad7d1763a71fda60c75d2d6391290cef28771589a81a2を.artifacts/ai-sigma/continuation-20261001/DEADLINE-20261002-1000/continuation-version1.mdへ保全。閉じた実験や旧個別契約の処理/提出期限、事前登録、旧失敗/逸脱を遡及延長しない。問い・所有者・許可範囲が大きく変わる課題は契約を更新し、正式比較は結果前に条件を固定する。同じ課題の許可範囲/総予算内の修正・再確認に毎回別契約を要求しない。統括.52が正本/Beads、steward.53が既存所有範囲の運用契約/config/reload/monitor更新と実反映を担当する。

## 現行の実行・記録

docs/development/ai-research-experiments.mdを適用する。課題/Git版/runを区別し、許可範囲・総予算内の修正版デバッグ/再現/性能測定を反復できる。必要な結果・ログと版参照を記録し、全コピー・全履歴hash・一律一回制限を義務にしない。正式棋力の成績選別・敗北の無条件置換を禁止する。旧実行の期限/成績は遡及書換えしないが、同じコード・入力・コマンド（旧80内容を含む）も現在許可内の新runで再現確認できる。進行個別許可差分・残予算はcoordinatorが明示する。研究ローカルGit管理可、製品main統合/push/公開不可。版3は文書運用だけの改定で、現行期限/CPU/RAM/LLM/保存/GPU/製品権限を拡張しない。旧版2SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987fは旧dispatch/履歴参照として保持し、現行83/84は本版3の実hashを継承する。
