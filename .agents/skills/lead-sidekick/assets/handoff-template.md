# Sidekick引き渡し

機械処理する状態と識別子は検証可能な構造化フィールドで保持する。本文から「完了」を推測して起動制御しない。

```text
Status: Ready for review | Blocked | Validation-blocked | Incomplete
Task ID / Attempt ID / Contract version:
Changes: 変更箇所と観測可能な動作
Evidence: 受入基準ごとの根拠、検証コマンドと結果
Tested state: commit、worktree、patchなど識別可能なコード状態
Remaining: 未解決・未検証事項、必要な最小のLead判断
Ownership: 書き込みを停止した対象、継続中の独立領域
```
