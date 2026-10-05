# Sigma研究contextの独立最終検証

quoridor-4lc.14 / SIGMA-CONTEXT-CRITIC / 試行1 / 版1。critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。目標契約 ai-sigma-research-goal.md版1の全文、common/critic/team/AI設計/storage/handoffを継承。目標quoridor-4lc継続。追加委譲0。

問いは.10最終contextの規約/Action/feature/内部探索整合性を独立runtimeで支持できるか。製品standard規約不変、比較専用Aの選択は継承。速度/棋力/達成を認定しない。.10は受入れ待ち、.7queue採用保留でliveはVecDequeに復帰済み。正式対戦はhistory/NN接続/deadline/参照/校正未成立につきno-go。

入力: docs/reports/ai-sigma-experiment-context.md SHA faf2585083b6b52fc3c7467d042f10140493fd712447524f7ad45c7b1e7ce5fe と今回契約を全文読む。固定golden fixtures SHA206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、game.js dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5。原run .artifacts/ai-sigma/runs/SIGMA-RULE-FEATURE-PARITY/ のartifact-manifest/final-binary-provenance/source snapshotが正本。最終native native-research-parity-final SHA a7878b1df2461eb3682022d7c319e46500482717e7b71d3b66fc501444a8ce90、research-wasm-final/sigma_research_bg.wasm SHA25d8b5c65ce6bb31b7d1656cedac673ca5c5aa8ed0aa3dcd9f9654f7af894f90、JS SHA2f43c150b7e6fbe2f622bd103b4be9ab04745d33d3ab8416462dd4bb373f437d。旧research-wasm/は最終版と異なるので使わない。

作業ai-sigma/codex/ai-sigma。原source/artifact/hashを前後照合しimmutableに保つ。書込みは .artifacts/ai-sigma/verification/CRITIC-CONTEXT/ とdocs/reports/ai-sigma-critic-context.mdだけ。自己copy helperは原コードを先に読み、絶対入力path/出力/temp/port/監視/guardだけ変更しdiff/hash保存。原analyzer/browser-jobは元rawを上書きするので直接実行禁止。core/ai/Wasm/bridge/製品/UI/locks/主checkout/他worktree編集0、build/取得/依存同期/NN/学習/対戦0。

最初に暫定短報告を保存。immutable nativeを自己出力へ実実行し、既存Chromium153でimmutable最終Wasmも直列実実行する。28件を合法20/人工history3/人工ply5に分け、長さ/ID/finite/型を先に検査。全648f32/各mask順序/136↔209/P2/履歴ply/raw-effective終端と遷移3187件をgolden/固定game.jsへ照合。探索trace769node/終端36の再取得と独立参照照合を優先し、rootだけの確認を全内部parityと言わない。node親子からoverlay/base根の二重count・兄弟history漏れ・全mask/終端優先・visits/value符号を照合。原verify-internal-nodes.mjsを読むが独立assertと出力分離を用意する。端末4rootのspy evaluate0/goal優先/draw0、cap fallbackの文脈と符号を原tests/source/rawから照合。既存immutable test binaryを安全に特定できれば自己logへ実行可、見つからなければbuildせずそのruntime範囲は未検証と残す。通常6case旧B0/currentoff/research通常constructorの不変を元rawと保存binaryの限定再実行で照合。全binary再実行が期限内でなければ未実行部分を明記し範囲を誇張しない。

from_prefixの合法性とfrom_countsの算術検証を区別。真に合法200手replay/実history no-legalは未完了、人工8件で代替完了にしない。terminal raw mask/遷移は診断、合法対局継続ではない。arena cap会計注入は実OOMでない。元VM/入力cap/clippy失敗、storageguard停止、自己新incremental244097024B整理、native correctnessとWasm build重なり、Beads読取/tmp逸脱後移動を保持。通常規約を変えていないことと全面契約成功を区別する。

25分: issue作成2026-09-30T20:55:51Zを保守起点。処理停止21:10:51Z、短報告/提出停止21:20:51Z、全体期限01:17:58.145139Z以内。15分処理+10分提出、最後に長文生成を始めない。短報告2000字程度、詳細はJSON。CPU2単1logical/jobs1/RAM2GiB guard1.75/新規128MiB guard112MiB/GPU0、hypothesis .13 CPU0/RAM2GiB/新規1GiBと並行、root含むLLM3、性能窓ではない。child120秒以下と残時間の小さい方、Chrome全子/PIDstarttick/RSS/affinity/一時保存監視、専用TMPDIR/TMP/TEMP/XDG所有先のみ、parentalive /proc/PID/cwd短aliasを使うなら事前realpath照合。自己HTTPが必要ならport5184を事前空き確認し自PGID/PIDだけ停止wait、全子残存/port解放とtemp残logを分類。RSS瞬間保証の限界保持。他者kill/証拠削除0。

開始ready/show目標/.14/.12、pauseなしなら.14だけclaim。.12は統括数値互換性限定受入れnotesを確認し本人close可、TMPDIR訂正と旧報告履歴は保持。.10/.7/目標/.1他者更新close0。停止後show目標/自子pause確認、backup、report --to coordinator --issue quoridor-4lc。.14は受入れ待ちin_progressを維持。新研究を自己起動しない。成功/未完了/不成立/予算逸脱を分けて返す。
