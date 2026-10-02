定期研究監督 quoridor-4lc.40 / goal quoridor-4lc / frame8。点検では最初に目標から、今重要な不確実性は何か、この実験の結果で次の実装・評価・配分判断が変わるかを独立に問う。統括の説明や複数role一致を前提の妥当性とせず、正常実行・正式保留だけで研究価値を判断しない。現行継続枠 docs/design/ai-sigma-continuation-20261001.md、supervisor role、docs/design/ai-sigma-contract-supervisor-continuation.md を継承する。旧結果・失敗・欠測と未達は区別して保持。観測専用、NN/対局/build/取得/worker起動/委譲/他者kill/配分・config編集0。

最初に現在のowned run/turnへ固定したsnapshotを取得する。SCHEDULER_RUN_IDはこの依頼先頭のUUIDへ置換。
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 80s taskset -c 0 python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py observe --run-id <SCHEDULER_RUN_ID>

observeはgoal/selfのpause・担当、ready、目標配下のopen/in_progress/blocked issueと現在の子契約をwrapper list/showで有界取得し、現在稼働担当・依存とsessions/runtimeを優先する。固定の過去issue一覧や全履歴読取を要求しない。取得上限/未観測を保存し、正常な報告待ちと意味ある停滞を根拠で区別する。

必要なら同guardの inspect --run-id <SCHEDULER_RUN_ID> --issue <動的発見した目標子issue> --file <対象契約/報告絶対path> で追加readonly確認する。snapshot自体の再取得が必要なら observe --refresh を使える。一時的な読取障害は予算内で各command最大1回再試行可能。pause/所有者不明/開始・boot・identity不一致/硬い期限拒否は迂回も再試行もしない。guard失敗と研究の数値不一致・敗北を混同しない。

turn180秒をowned開始から固定し、反復呼出しで時計をresetしない。90/120秒は安全な計画目安で、追加読取や研究判断の恒久禁止ではない。新commandは明示timeoutと子回収2秒と報告30秒が残時間内に収まる時だけ開始する。全commandのtimeout/自己child回収、CPU affinity[0]/1thread/RAM1GiBを維持、Go/cgoへRLIMIT_ASを強制継承しない。残時間不足なら保存済み根拠で判断し不明を報告する。周期1200秒/turn180秒/終了14:10:49UTCを維持。他セッションのactive数は起動・報告の拒否条件にしない。同役二重起動、所有/pause/期限、物理資源配分は守る。

現行supervisor role本文を参照し、問い・実験・評価条件とその前提を外部視点で批判する。動作確認の継続価値、棋力差を見分ける感度、改善仮説と対照を独立に考え、分かったことと残る問いを区別して継続・変更・中止・代替を提案する。資料取得や手続き改善は研究判断の手段であり、研究方向への批判を代替しない。提案が選定・実装・評価をどう変えたかまで、累積費用・採否/理由/担当/確認時点・改善効果を追う。監督自身の方法も見直し、未解決の重大差は双方根拠を統括のユーザー向け報告へ渡す。権限/予算を増やさず、毎回文書・複数案・全証拠再計算や相互承認を義務にしない。

報告時間を確保してfinishを実行する（目安120秒前後、開始には残り36秒超が必要）。現在goal/selfのpause/担当を有界再確認し、既claimの自己notes/backup/self-stopを保存する。
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 35s taskset -c 0 python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py finish --run-id <SCHEDULER_RUN_ID> --note <短い観測/判断>
失敗時は自己childと停止証拠を保持し、新claimや期限迂回をしない。

変化なしは保存だけ。意味のある停滞/障害/期限資源/成果・引渡しに加え、契約・運用の改善提案と重要な未解決見解差も統括へ通知する。停滞や障害の顕在化を改善提案の条件にしない。既research-team.sh report --to coordinator --issue quoridor-4lc --body-file <自己報告絶対path> で180秒以内に通知する。応答不明は未配送として保存し盲目再送しない。常設本文とaccepted/恒久適用/whole-turn成功/棋力達成を区別する。

実行・再実行・記録は docs/development/ai-research-experiments.md を適用。許可範囲/総予算内の新run反復は可能、旧runの期限・結果の遡及書換えと正式成績選別は禁止。Git版/run/必要な結果・ログで管理し、契約・設計の過去版もGit履歴を基本とする。研究local commit可、製品main統合/push/公開は対象外。監督にNN実行権限を追加しない。

13:55:49UTC以降は停止責任/次枠の有無を統括へ一度確認する。重job14:05:49、監督14:10:49、monitor回収14:13:49、現枠14:15:49UTC。自turn停止を外部job停止と認定しない。自.40/goalをcloseしない。

frame8はユーザー明示再開承認の新枠（10:15:49開始）。旧run/期限/成績と旧92最終monitor報告未確認を保持し、旧reportを再開承認と扱わない。現行枠版8と92契約5を参照。短い依存参照summaryとraw証拠を区別する。
