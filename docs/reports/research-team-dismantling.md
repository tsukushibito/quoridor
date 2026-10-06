# 固定研究チームの解体とタスク単位運用への移行

2026-10-06、Beads `quoridor-1gj`。ユーザーが「316・317を引き渡して終了」を選び、Rootが実施した。研究を進める追加許可ではなく、組織と運用の終了・ソフト整備である。

## 終了と保存

310の学習実測、315の描画統合、316の次期提案、317のTT計測ソフト修正を有限に引き渡した。旧Coordinatorの最終commitは `6e8d4ab5ac1a3305eff66e4c5b72dd36bfb06b28`。指定55pathをRootもcurrent/blob/SHA一致で確認し、明示されたGit/index・source所有解放を受領した。[最終引渡し](../../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)。モデル・入力・科学データ・必要archive・共有環境・DB・managed worktreeの削除は行わない。

Stewardが02:00:20 UTCにscheduler2269819/starttick50428490とmonitor2271322/starttick50433272の不在、state stopped/ownednull、Supervisor idleを確認した。[停止証拠](../../research-data/ai-sigma/frame24-steward/1gj-terminal-runtime-stop-v1.json)。Rootの後続観測でも旧scheduler/watch/job controllerの一致processは0だった。特定processの停止と全host・将来の停止保証を区別する。

公式App Serverの`thread/archive`で旧6セッションを全てアーカイブした。会話を削除せず、IDと実archive応答を保管した。[セッション記録](../../research-data/ai-sigma/team-dismantling/retired-sessions.json)、[archive receipt](../../research-data/ai-sigma/team-dismantling/session-archive-receipts.json)。旧registryは正確な内容・SHAをこの非運用記録へ保存した後、現役pathから撤去した。

## 現役経路

固定role/common/templateと専用team client・定期scheduler・watch、その専用tests/examplesを撤去した。旧sourceは最終commitとの一致を確認してから削除し、[Git復元参照](../../research-data/ai-sigma/team-dismantling/removed-source-git-references.json)を残した。過去版互換shimやrole registryへのfallbackは作らない。環境は既存の物理pathをそのまま再用し、依存version・共有学習環境は変更しない。

新しい `research-session.sh` は明示threadとBeads issueでcreate/send/status/read/wait/archiveを行う。sendは担当・状態・pauseを配送直前まで確認する。createは未担当または操作元が所有するissueのみ、CAS付きで新threadへ移譲して実タスクを開始する。固定persona・準備だけのLLM turn・定期LLMは作らない。

`research-job.sh`はregistry/roleを廃し`thread_id`で担当へ束縛する。実行・期限・取消・正確な子回収・上限付きログ・永続結果・完了通知の重複抑止を維持する。scheduler内の必要な低水準処理は `research-runtime.py`へ抽出した。保存予算や科学権限をツールが勝手に追加することはない。[タスク設計](../design/ai-research-team.md)、[ジョブ運用](../development/research-jobs.md)。

## 状態と判断

旧92・40のstanding運用とRoot314の引渡しを終了した。古い18件のin_progress課題は、成果を完了認定せずRootの再整理待ちdeferredへ移した。履歴snapshotと移管理由を保管した。[旧状態](../../research-data/ai-sigma/team-dismantling/retired-task-state-before.json)、[移管記録](../../research-data/ai-sigma/team-dismantling/retired-task-transfers.json)。期限切れleaseは対象IDだけreclaimし、leaseを持たない旧claimは本人セッションの恒久退役を確認した上で引き継いだ。途中のCLI ownership/flag拒否は状態移管を成功認定せず、適切な経路で修正した。

最高棋力の目標 `quoridor-4lc` は未達・openのままRootへ引き継いだ。研究実行は未配分。旧許可・残GPU秒・ready状態で再開しない。GPU新3600秒の消費13.493288946秒/残3586.506711054秒、旧7200秒UNKNOWN・保管UNKNOWN128MiB・旧費は原証拠で保持する。[資源引渡し](../../research-data/ai-sigma/frame24-steward/1gj-final-resource-handoff-v1.json)。

Rootが人間との窓口、作業調整、統合を兼ね、必要時だけ実行担当と独立レビューを依頼する。重要な研究方向・データ・学習・モデル変更は観測と競合案・全費から人間が選ぶ。現在状態は[既存の現在計画](ai-sigma-coordinator-current-priorities.md)へ一本化した。316の公開全域多様性調査は提案のまま、取得・decode・新学習・対局は開始していない。

## 検証

Rootが変更範囲を独立に確認した。実モデル・GPU・科学jobは起動しない。

- session/jobの人工短process・fake RPC35件PASS：担当・pause・期限拒否、CAS移譲、idle/active/archival、取消・子回収、失敗、応答不明後の二重配送抑止。
- 資産resolver6件・source export3件PASS。共有資産の場所は不変。
- Python AST34file・JavaScript構文3file、依存境界、Ruff format/lint、Prettier、変更docのローカルリンク、diffcheckを確認。
- Shellは既存2スペース形式へ手整形し`bash -n`で検証。shfmtは未導入で、追加取得は行わない。
- 全6旧sessionのarchive応答、旧正2process不在、現役registryなし、旧専用実行sourceなしを確認。旧科学の未確認・失敗・超過を新しいsoftware検証へ読み替えない。

引渡し停止、必要な明示pathの通常Git保存、Beads更新・backupで完了する。今後の研究の再開・予算追加・最高棋力認定はこの解体の完了と区別する。
