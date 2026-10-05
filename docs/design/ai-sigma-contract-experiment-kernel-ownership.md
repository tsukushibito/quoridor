# SIGMA-KERNEL-OWNERSHIP / quoridor-4lc.54 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。[継続版2](ai-sigma-continuation-20261001.md) SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。新全体終了2026-10-02 01:00UTC、重job00:50/監督00:55。旧.49/.51個別期限・失敗は遡及延長0。今回は新所有境界の判別実験、棋力/対局採用を認定しない。

根拠: .51 manifest db492ac61f368693e5f66cdfdde46d34e21ef3d8b97e605222ed8a6202a51cfe / report642d923d76a1f497c1e017310a47cca9a49d1af9671ebb6bff66447bb79050f0。fixed5は最初の正常2＋T10拒否後に高速detach子2件の親子履歴を取得できず UNKNOWN_ADOPTED_OWNERSHIP_REFUSED。現在不在/monitor remaining=[]は制御回収成功ではない。旧.49 g287>91/非uniform62+82、.50独立no-goを保持し.48事前登録不変。root受領 proof DEADLINE-20261002-1000/nogo-evidence-receipt.json は50の1334/51の667 checks現在一致（親版2の明示変更だけ例外）、8identity不在、全866root再監査ではない。

問い/競合: 高頻度の祖先poll/ACK事前登録では高速fork/exitを見逃す。新規・一job専用subreaperが起動時に子を持たず、一つだけの明示jobrootをspawnしているなら、カーネルがその専用親へadoptした直接子を所有根拠にできるか。観測された直接子/起動時排他/bootPIDstarttickと待機の根拠を合わせる。名称/profile/同UID/PGIDだけを根拠にする案は採用しない。方式の具体化は担当判断、証明できなければfail-closedを返す。

一次根拠（統括読取、runtime実証ではない）: https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html は orphan が最も近い生存subreaper祖先へreparentされる契約、https://man7.org/linux/man-pages/man2/waitpid.2.html は呼出しプロセスの子のwaitを定義する。専用launcherが単一job由来しか持たないという限定から所有を導くのは研究仮説であり、本書で成立を認定しない。必要な限定text読取/既存man読取は可、model/runtime取得なし。

書込は新 tools/ai-sigma-kernel-ownership/、continuation-20261001/SIGMA-KERNEL-OWNERSHIP/、報告 docs/reports/ai-sigma-experiment-kernel-ownership.md。旧.51/source/raw/ACK拒否・.49/45/43証拠は不変snapshot/hashで固定し、共有製品/主checkout/scripts/rootlock/モデル/NNbinary編集0。新launcher/監視/ownership/cleanup境界と診断/mainコピーだけ変更可。kernel/worker/owned checkpoint/RuleA/PUCT1.5Q0/seed1979/limits/T500g91/watchdog/責任/最終配送stampは同bytes維持。新域の.51由来未知adoptedの扱いは旧成功への修正ではなく、新証拠の所有種別として記録。未知の全ホスト子へsignal/waitしない。

dummy先行gate: 新プロセスで起動child空・subreaper設定returnとPR_GET確認・唯一の直子jobroot・bootstrap排他を記録。launcherが他jobroot/無関係なhelperをspawnした場合は所有境界を無効にしfresh禁止。doublefork/即親exit/setsid/PGID変更/TERM無視/Z→self wait/PID0/自然exit/既signalCode/idempotence、未poll祖先でのkernel-adoption、外側別ownerからspawnしたnonownedの非adoption・非signal・非wait、PID再利用/偽登録/境界不明時fresh禁止を判別する。kernel child関係やwaitid等の実記録とPID/starttickを保存し、kill直前identity再照合。従来absence1000ms/drain100msを緩めない。子のexit保存とwait対象の排他を分ける。採用した方式の反例/限界を明記する。

dummy/境界が成立した最終sourceを凍結してから、同main正診断tokenによるfixedinitial5を一回だけ実行してよい。両engine通常T500g91→candidateT10g0/stepdelay500→stop/wait/controlledPID0→fresh load/warm/reclock両engine。最初と最後の全owned回収・無応答公開Action=null、fallback0/厳密value/所有checkpoint/post-validation stampを確認。失敗時は実NN再試行0・fresh禁止、自己領域/来歴保全/所有証拠がある子だけ回収。model/kernelsを変更して通さない。dummy補助バグは原因別一回修正可、元失敗保存。clockgate/g適格をこのfixed5で認定しない、actual_go=false/holdout・対局0。新均一校正と比較事前登録は後続別契約。

資源 CPU2単logical/RAM4GiB guard3.5、準備もCPU2・jobs1、新128MiBguard112は既存entry2GiB予約内/追加0・累積12GiBを維持。steward.53はCPU0メタデータ運用だけ並行、正式無競合速度とはしない。TMP/XDG自己領域、20ms観測＋instantpeak限界、同時NN1系列のみ。dependency/build/model取得/GPU/学習/対局/追加委譲/他者kill/旧証拠削除0。既存toolchainとNode/Python標準ライブラリのみ。cgroup/PIDnamespace/共有システム変更はこの契約で実施しない。

処理は受領60分または14:10UTCの早い方、報告70分または14:20の早い方、新job5分前停止。実NNjobはready/load/5要求/cleanupの上限を事前固定し180秒以内、残契約で収まる場合だけ起動。dummyは各短timeout/同期回収。deadlineを拒否されたjobは再起動/期限延長0。原inputbeforeafter・source/buildなし来歴・PIDbootstarttick/PPID/子/wait/status/exit・全failure・資源/stopを本文より先保存。stopped=falseなのに本文で完了としない。

自.54のみclaim。統括は.50 no-go監査を限定受入れ（時計g287失敗/回収未成立の証拠）、.49は本人が失敗理由を保持してclose可。.51は限定negative方法証拠受領でclose可、未知への拒否を正しさ成功として格上げしない。close理由に今回rootチェックの限界を記載。goal/他者issueclose0。全新操作backup/report、独立critic前は採用/実run禁止。終了後の通常詳細再承認は不要、次の検証配分は統括へ。
