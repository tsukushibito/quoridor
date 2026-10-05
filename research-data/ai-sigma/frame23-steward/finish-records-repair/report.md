# Supervisor finish receipt改善の採否

quoridor-4lc.92。同run48a8c153の小receipt改善を採択し、prospective patchを準備した。現在科学guardが参照するwatchは24期待hashに含まれるため、本体・期待binding・runtimeは変更せず、停止再起動も行っていない。実適用と自然finishの効果は未確認。

## 観測と原因の範囲

原outer25秒timeoutはexit124で、原childwaitは欠測。後のexactargv不在とone retryの5wrapper exit0/reapedはその時点の証拠であり、原timeout時の回収証拠を補完しない。原4JSONのpath/bytes/SHAは`diagnosis-and-admission.json`を参照し、原本は変更していない。

現実装ではwrapperを別sessionで起動し、finishの5command記録を最後に一括保存する。captureのfinallyはpipeを閉じるだけで、外側SIGTERM/例外で終了するとchild waitと途中の完了receiptが欠ける経路がある。beads.shはflock経由でexecする。この経路は今回の欠測と整合するが、原timeoutが何番目のcommandで発生したか、原childが実際にどう終了したかは不明。

## 候補patch

`research-watch-prospective.patch`は現watch SHAを基準とした差分で、source複製をGit保存しない。各wrapperの既command ordinalごとに最大4KiBの小receiptを確保し、reserved→started→completedを同pathへ原子的に更新する。command全文はhash/bytesへ、stdout/stderrは読取byte数/hash/完全性、exit・PID/tick/boot・wait結果を残す。後続commandで停止しても先行commandのreceiptは残る。

observerのSIGTERM/SIGINTを捕捉し、captureのfinallyで正確な直接childにだけTERM→有界wait→必要ならKILL→有界waitを行う。元signalによる失敗を成功に変換しない。monitor固有signal処理は置換しない。捕捉不能なSIGKILL/host停止ではstarted receiptが未回収のまま残る。直接childのwaitを子孫process全不在へ変換しない。identity不明/不一致ではsignalを送らず、回収不成立を記録する。

64KiB record/512KiB run/24commandと既通信timeout・期限・資源guardは維持。小receipt確保で容量拒否ならspawn0、後の保存拒否もtyped不足。24command分のreceipt原子的更新を含む割当上界は294,912Bで、既run cap内の現在量とのadmissionが引き続き必要。新receiptを足した全runが必ず収まるという保証ではない。

## 検証と費用

隔離candidateで新6mock＋関連既8契約チェック14/14 PASS。mockは実Popen・signal・RPC・DB・科学を起動しない。正常完了、soft中断時の回収、identity不明の非signal、有界KILL、容量拒否spawn0、後続停止でも先行receipt保持を確認。project Ruff format/check、patchのgit apply --check PASS。実SIGTERM下の自然finish効果は未確認。詳細は`mock-check.txt`。

自己現在保持＋既remaining＋新source/小記録/uniqueGit forecast256KiBは112MiB内。点観測の実量はJSONに保存。適用時のCPU0単1軽管理・mock/validateは60秒以内目安、RAM1GiBと既期限を維持し、fresh current/remainingを再確認する。

再現は現基準watch SHA一致を確認し、live sourceへapplyせず隔離出力へ復元する：

```bash
patch --output=.artifacts/research-team/finish-records-repair/reconstructed.py \
  scripts/dev/research-watch.py \
  < research-data/ai-sigma/frame23-steward/finish-records-repair/research-watch-prospective.patch
WATCH_CANDIDATE_PATH=/workspaces/quoridor/.artifacts/research-team/finish-records-repair/reconstructed.py \
  UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  /home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B \
  research-data/ai-sigma/frame23-steward/finish-records-repair/test-prospective.py -v
```

## 適用機会と責任

ownerは既92。科学job・読者・current guardが自然停止し、Supervisor公式idle/正ownedなしを確認できる窓で、正scheduler/monitorを秩序停止して旧証拠を保持。その後source/必要限定testを反映・整形・検証し、watch期待SHA/bindingを整合、validate→既通常入口で再開→loaded/current24hash/正2identityを確認する。次の通常finishの各完了receipt・notes・backup・wait到達で効果を確認し、強制tickは行わない。

自然Supervisor idleだけでは科学midjobのguardを変更しない。窓が成立しなければ未適用の担当92/終了準備または次の明示許可運用機会へ引き渡す。23:26:03 heavy/23:31:03監督/23:34:03monitor/23:36:03保存を変更しない。Coordinator恒久idle refresh pendingは別責務として保持する。Root ACKや全役承認を科学入口に追加しない。
