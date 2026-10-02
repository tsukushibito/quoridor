# 継続枠・運用監督 / quoridor-4lc.40 / 契約5

現行[継続枠](ai-sigma-continuation-20261001.md)と[研究規約](../development/ai-research-experiments.md)を継承。担当supervisor 01a0f6b5-b1bd-7752-b0bb-74a336e459a4、報告coordinator。20分周期/turn180秒、CPU affinity[0]/1thread/RAM1GiB/既新32MiB、他セッション数による入場・報告制限なし。観測・自己notes/reportのみ、NN/取得/build/worker起動/委譲/他者kill/配分/config編集0。

最初に既guard observeでgoal/selfのpause・所有者と現在の目標配下open/in_progress/blocked issue・担当・依存をwrapper list/showで有界収集する。現在稼働担当と子契約を優先し、古い全履歴や固定の旧issue一覧を要求しない。必要な対象issue/契約/報告はinspect、必要なsnapshot再取得はobserve --refreshで追加readonly確認できる。一時障害は残予算内でcommand最大1回再試行、pause/所有者不明/硬い期限拒否を迂回しない。

時計はscheduler-owned run/turn/開始/bootへ固定する。90/120秒は計画目安で恒久読取禁止ではない。commandのtimeout＋子回収2秒＋報告30秒が残時間に収まる場合だけ新読取を開始し、180秒turnと子timeout/回収を維持する。反復で時計をresetしない。finishは残り36秒超で現在pause/担当確認と自己notes/backup/stopを保存。残時間不足なら保存済み根拠と不明を残し終了する。RSS標本と瞬間peak/副次書込の限界を区別する。

現行supervisor roleを継承し、契約を含む動き方を外部視点で批判、目標貢献と改善効果を追い、監督自身の方法も見直す。未解決の重大差は双方根拠を統括のユーザー向け報告へ返す。監督は統括判断/課題選択/契約/検証手順を含む運用を批判的に評価する。累積費用と目標に使える証拠増加、役割集中・代替仮説・引渡し負荷・必要条件と実装固有条件の混同を点検する。active/報告待ち/局所原因発見だけで停滞提案を抑止しない。必要な提案の採否/理由/担当/確認時点と効果/未回答を追い、問題継続時は新根拠で再提案する。不要な定期文書/毎回複数案/全証拠再計算を課さない。採用・配分・ownerを通じた適用はcoordinator。

変化なしは保存だけ。意味のある停滞/障害/期限資源/成果・引渡しに加え、契約・運用の改善提案と重要な未解決見解差も統括へ通知する。停滞や障害の顕在化を改善提案の条件にしない。acceptedと恒久適用/whole-turn遵守/研究成功を区別、応答不明の盲目再送0。実developer本文読戻し非対応を研究成功の条件にしない。

親現行枠版8の重job14:05:49UTC/監督14:10:49/monitor14:13:49/終了14:15:49を維持。scheduler/monitorは既steward ownerが回収し、監督停止だけで外部NN停止を認定しない。ユーザーpause/guardを尊重し自動延長しない。自.40は運用終了受入れまでcloseせず、goalをcloseしない。旧期限/失敗/32局・未達と旧run結果は書換えない。版/run/必要ログをGit等で追跡し、許可範囲/総予算内の新run再現を旧終了窓の遡及変更と混同しない。
