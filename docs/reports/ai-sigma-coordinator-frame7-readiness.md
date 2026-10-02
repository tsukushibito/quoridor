# 枠7の起動受入れと研究開始

現行枠は2026-10-02 06:12:31～10:12:31 UTC。root108は起動準備を独立確認してcloseした。統括は通常研究を継続し、個々の研究でroot再確認を求めない。

107は契約4を06:21:46に受領・開始した。Chrome全体をRAM4GiB/current RSS guard3.5GiBに含め、旧896MiB配分失敗を維持して新runへ進めた。担当の新preflight報告は実ブラウザのsecure context/cross-origin isolation、SAB/AtomicsとWorker共有、未完成・取消・旧世代の拒否、mainの4ply mock/goalを支持する。実AI機能runはGit81401c29b2dde5fa7545fd28eb14012d57e3431fで開始したが、結果は未受領。旧Node mockと今回の実ブラウザpreflight、実AI、棋力を分ける。

92は契約3を06:22:02に受領した。06:27:16.944781にrunning/reloadedとloaded config/contractを保存し、統括も24期待hashの不一致0、新scheduler2167898/start17534107・monitor2168144/start17534922の同identityを確認した。周期1200秒/turn180秒/active数拒否なし。旧最終monitor報告未確認と未来停止未観測は保持する。起動受入れは運用全期間成功や外部NN停止の認定ではない。

初回監督turn01a0fb4b-9c4e-7dd0-b640-761b41dd2f83は06:27:11.575884にdispatch、06:30:14.668803にinterrupted。正常な点検完了とは扱わない。実入場、期限による回収、点検本文の成否を分け、今後の運用報告で理由・効果を追う。点検内容だけのために新しい独立層を設けない。

研究報告待ちは107の既experimentから統括への機能run/診断対局結果、長期停止報告待ちは92の既steward。新重job開始停止10:02:31、監督10:07:31、monitor回収10:10:31、証拠保存10:12:31を92が所有する。CPU4/RAM8GiB/保存12GiB、採用済みWorker探索+SAB・browser main対局/採用/判定・外Node起動監視保存の分担を維持。正式公平性/NI/Sigma同等は未認定。

根拠: `.artifacts/ai-sigma/resume-20261002/frame7-readiness-verified.json`、107/92の実delivery記録と本人ACK、92 `frame7/live-applied.json`・`live-frame7-675e30ad-4d75-46ea-bb27-0a3ed934aee0/first-live-turn.json`、root `.artifacts/research-team/resume-20261002-061231/root-acceptance.json`。課題状態はBeadsを正本とする。
