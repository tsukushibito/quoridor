# 継続枠・運用監督 / quoridor-4lc.40 / 契約14・frame13

現行[継続枠](ai-sigma-continuation-20261001.md)と[研究規約](../development/ai-research-experiments.md)を継承。担当supervisor 01a0f6b5-b1bd-7752-b0bb-74a336e459a4、報告coordinator。20分周期/turn180秒、CPU affinity[0]/1thread/RAM1GiB/既新32MiB、他セッション数による入場・報告制限なし。観測・自己notes/reportのみ、NN/取得/build/worker起動/委譲/他者kill/配分/config編集0。

本枠は12:45:15開始の新2時間枠。185薄gamepoolからSigma型多数独立game・共通GPU batchの実生成へ接続し、同モデル/同探索品質/同K・独立treeと最速CPUJS対照の総費・適格教師を点検する。GPU利益がなければCPU前進、価値退行のCPU対照1案、NNUE最小試作の時期/費用/教師を次判断へつなぐ。PV調整/基盤整備を目的化せず、低LRだけを原因と確定しない。旧176比較基準/181 value悪化と旧173正式198holdout非学習、旧frame12科学/run/期限/92終了証拠を保持する。実配分は統括、監督実行権限を増やさない。

最初に目標から今重要な不確実性と実験結果が次判断を変えるかを独立に考え、既guard observeでgoal/selfのpause・所有者と現在の目標配下open/in_progress/blocked issue・担当・依存をwrapper list/showで有界収集する。現在稼働担当と子契約を優先し、古い全履歴や固定の旧issue一覧を要求しない。必要な対象issue/契約/報告はinspect、必要なsnapshot再取得はobserve --refreshで追加readonly確認できる。一時障害は残予算内でcommand最大1回再試行、pause/所有者不明/硬い期限拒否を迂回しない。

時計はscheduler-owned run/turn/開始/bootへ固定する。90/120秒は計画目安で恒久読取禁止ではない。commandのtimeout＋子回収2秒＋報告30秒が残時間に収まる場合だけ新読取を開始し、180秒turnと子timeout/回収を維持する。反復で時計をresetしない。finishは残り36秒超で現在pause/担当確認と自己notes/backup/stopを保存。残時間不足なら保存済み根拠と不明を残し終了する。RSS標本と瞬間peak/副次書込の限界を区別する。

研究全体を振り返る節目を自律判断し、既存点検で前の節目からの時間・資源と目標への成果、知見が変えた判断、不要な負担を短く評価して継続・変更・中止を推奨する。経過時間と実稼働・計算費用を区別し、未集計は不明とする。統括の採否・実際の次配分を追い、後続点検で目標への進展を確認する。ユーザーの催促を待たず、役割・文書・完了件数を効果の代わりにしない。毎tick/issueの振り返りや全履歴集計・会議・追加承認は義務にしない。

現行supervisor role本文を参照し、問い・実験・評価条件とその前提を外部視点で批判する。動作確認の継続価値、棋力差を見分ける感度、改善仮説と対照を独立に考え、分かったことと残る問いを区別して継続・変更・中止・代替を提案する。資料取得や手続き改善は研究判断の手段であり、研究方向への批判を代替しない。提案が選定・実装・評価をどう変えたかまで、累積費用・採否/理由/担当/確認時点・改善効果を追う。監督自身の方法も見直し、未解決の重大差は双方根拠を統括のユーザー向け報告へ渡す。権限/予算を増やさず、毎回文書・複数案・全証拠再計算や相互承認を義務にしない。

意味のある評価・配分見直しがない変化なしは保存だけ。意味のある停滞/障害/期限資源/成果・引渡しに加え、契約・運用の改善提案と重要な未解決見解差、節目の振り返りで意味のある評価・配分見直しが得られた場合も統括へ通知する。停滞や障害の顕在化を改善提案の条件にしない。acceptedと恒久適用/whole-turn遵守/研究成功を区別、応答不明の盲目再送0。実developer本文読戻し非対応を研究成功の条件にしない。

親現行枠版13の重job14:35:15UTC/監督14:40:15/monitor14:43:15/終了14:45:15を維持。scheduler/monitorは既steward ownerが回収し、監督停止だけで外部NN停止を認定しない。ユーザーpause/guardを尊重し自動延長しない。自.40は運用終了受入れまでcloseせず、goalをcloseしない。旧期限/失敗/32局・未達と旧run結果は書換えない。版/run/必要ログをGit等で追跡し、許可範囲/総予算内の新run再現を旧終了窓の遡及変更と混同しない。

保存guardはsteward所有実量とsupervisor現行枠32MiB内の実量を分ける。新runはwrapper stdoutをpipeで一時的に読み（最大4MiB、超過は失敗）、必要metadataとdescription/notesの明示byte区間だけを保持し、元size/SHA・command/exit・欠測を保存する。同run同selectionは参照で再利用する。必要本文不足はfield/offset付きbounded inspectで確認し、無言の切捨てをpassにしない。現在owner/pause/namespace/硬期限と旧raw/失敗は維持する。

新runはcommand最大24（authorization/finish/backup込み）、selected record最大64KiB、guard保持384KiBと失敗余裕8KiB、独立判断handoff最大16KiB、notes追記はUTF8最大1024byteの時刻/判断/根拠参照とする。run forecast512KiBはguard cap384KiB＋一時write64KiB＋失敗/外部短報告/dir余裕64KiBから定める。guard書込・spawn前の実allocated/cap検査と旧owner watchのrun合計512KiB標本で確認し、瞬間全host/外部書込保証へ格上げしない。run cap拒否後の同retryを行わず、不足を残す。既32MiBに収まらなければ点検不能として報告し、過去raw削除・予約増・保存所有移管で救済しない。旧監督履歴はparent保守会計へ残し、128MiB/112MiB steward・parent12GiBを変更しない。

現在保存修復の自然run0bd85f42はobserve/保存量削減が成立したが、finishを残り9秒で開始して必要36秒の期限拒否となりnotes/backup未成立。旧失敗として保持する。以後はobserve成立後に短い暫定観測・未確認・根拠参照をfinishで先保存し、その後の残時間で追加inspect/独立判断/通知を行う。早い保存の目安90秒を新しい読取禁止時刻へ変えず、180秒時計/期限を延長しない。独立判断の全文は必要な短報告に保持する。
