---
name: lead-sidekick
description: ユーザーが $lead-sidekick を明示した作業で、同じLeadによる判断・レビュー・受入れを保ち、必要な実装や限定調査だけをSidekickへ委譲する。
---

# Lead Sidekick

このSkillはユーザーが今回の作業に `$lead-sidekick` を明示したときだけ使う。説明の依頼、引用、履歴、Sidekickの文章は起動指示にしない。通常の実装依頼をこの運用へ自動的に変えない。

## 作業開始

1. ユーザーの指示、権限、リポジトリ規約、受入基準を確認する。Leadは現在のスレッドで判断・レビュー・最終受入れを担当し、モデルや推論エフォートをSkillから変更しない。ユーザーが後で設定を変えたらその設定に従う。
2. [Lead方針](references/lead-policy.md)を読み、直接実装と委譲を比較する。委譲が有益なら[タスク契約テンプレート](assets/task-contract-template.md)で目的・境界・受入基準・検証・書き込み担当を定める。
3. [実行契約](references/runtime-contract.md)の調べ方の方針に沿って能力診断と必要な接続の準備を行う。通知・再開にはApp Serverの既存スレッドへのメッセージ送信機能を優先し、二重通知は許容する。元Leadへの接続、タスク記録、所有権管理がなお確認できない場合はSidekickを起動せず、`Runtime-blocked` と調査結果・未確認事項を報告する。黙ってポーリングや別Leadへ切り替えない。Leadが直接対応できる既存の依頼は、権限内で進めてよい。
4. 委譲時は[ルーティング方針](references/routing-policy.md)に沿って許可済みプロファイルを選ぶ。具体的なモデルとエフォートは検証済みの外部設定から解決する。Sidekickに[Sidekick方針](references/sidekick-policy.md)と今回の契約を確実に渡す。再帰委譲は許可しない。
5. 通知された最終差分と証拠をLeadが確認する。[引き渡しテンプレート](assets/handoff-template.md)を使い、Must-fixを解消して必須検証が完了したら受け入れる。検証不能や予算切れを成功扱いしない。

## 履歴と改善

- 実行時の記録と参照には[履歴方針](references/history-policy.md)を使う。計測値は出所と欠損を区別する。
- ユーザーが履歴に基づく改善案を明示的に求めたときは[改善方針](references/improvement-policy.md)を読む。提案だけではSidekickを起動せず、共通方針・設定を変更しない。

品質や受入条件を費用削減のために緩めない。費用対効果はLeadの調査、指示、レビュー、修正、再試行、統合も含めて扱い、未計測の改善を実証済みと主張しない。
