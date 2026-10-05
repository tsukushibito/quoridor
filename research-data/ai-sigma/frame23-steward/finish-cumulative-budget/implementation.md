# finish累積予算のprospective実装

92採択の静的案を `prospective.patch` に実装した。現役watchとtestsの元版・差分適用後SHAは `patch-base-and-proposed.json`。現役source/24期待hash/registry/config/contract/runtimeは変更していない。通常Gitは統括のみ。

## 挙動

finishのnotesは最大1025byteだけ読んで1024byte上限を先に判定し、超過ではadmit/show/子起動をしない。認証は `show quoridor-4lc quoridor-4lc.40 --json --brief-deps` 一回。ID集合・件数・型、状態、pauseラベル型と内容、現在registryの統括ownerとbindingのSupervisor ownerを検査する。自己課題は同finishで再利用し、既conditional-assignee/statusのappend後にbackupする。observe/inspectの判定内容は今回変えない。

既outer25秒の開始に対し一つのmonotonic deadlineを使い、各captureで起点を取り直さない。既10秒余裕を回収6秒と記録4秒として残し、inputhash/state/保持量/RSS、予約record、選択と認証の前後で残量を検査する。各子のtimeoutは残量から縮小、capture内部も同絶対deadlineを使う。TERM/KILLの各waitは3秒と累積回収残量の小さい方、回収recordはwork残不足でも試行する。各wrapperの最新admitとexactowned run照合を保ち、CPU/保持/pause/期限を飛ばさない。

各phase/capture/reap/receipt費は既出力内へ短く記録する。残不足はtyped unavailableとspawn拒否。同期のfilesystem/DB読取や起動前のinterpreter費には現状保証済上界がないので、全経路25秒達成や未来自然finishを認定しない。最終保存がdeadlineを超えた場合もobservedをunavailableへ訂正する。soft停止後の回収費、hardkill等の欠測と、正常なnotes/backup到達を区別する。

既runのcommand receiptにappendがあれば、確認済み/不明を分けて重複再追記を拒否し、原receiptと履歴の確認へ渡す。応答不明を成功とせず、自動再送しない。backup not_reached/outcome_unknown/completedは `finish-backup.json` の小receiptにも残す。別backup成立を元wholefinishへ付け替えない。64KiB/512KiB/24command/1024notes/outer25/period1200/null/運用deadlineは不変更。

## 検証

既14＋新12＝26mock tests PASS、1.735007秒/CPU0.159110秒、RSS peak45,297,664byte、CPU0単一/RAM1GiB/CPU60秒制約内。NN/GPU/build/科学なし。ID重複/欠落/foreign、owner/status/pause不一致、notes先行拒否、admit費によるspawn0、縮小timeout、同owned変更、append確認済み/不明の再追記拒否、backup不明、回収残量、保存超過を検証。Ruff format/checkと構文import、patchの `git apply --check` PASS。隔離runner初回の依存symlink不足とunittest0件の管理失敗を `test-result.json` に残し、明示module discoveryへ修正後の26件を成立点とする。

本番では次自然observe/finishの段階費、notes/backup各receipt、原失敗との違いを確認する。今回mock PASSを本番成果へ代用しない。

## 安全窓と未適用

19:42:31の公式Supervisorはidle/latest completed、state ownednull/running/24一致。19:43:29の同UID対象proc点にはpublic-z-learningのresearch-job管理process 1752325/48003800、1764200/48056006、1803526/48192044が現在存在した。これをNN実行中や全host未来不在の証明にはしないが、watch/sourcebindingの読者回収済みとも扱わない。旧19:16/25のstop点をfreshquietに使わず、科学/管理guard readerの自然waitと最新owner点証拠が揃う次安全窓までlive未適用pending。

owner92が自然科学reader停止＋正式Supervisor idle/ownednullの直前確認後だけ、既own2 orderlystop→patch/24期待binding→validate→normalstart→実loaded/exact2を行う。必要余裕不足は理由/owner92/次自然機会又は終了準備へ渡す。現在validな旧sourceでの科学をpending待ちにしない。23:26/31/34/36:03回収責任は維持、Coordinator恒久idle refreshとは別pendingである。

必要新source/Git/小証拠/temp上界256KiBは既112MiB current+remaining内に事前admit済み。新予約/新helper/層/依存/モデル設定/予算を足さない。通常保存は差分と必要証拠だけで、現役source全文の恒久二重コピーは作らない。
