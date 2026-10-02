# Quoridor AI研究チーム

決定日: 2026-10-01（日本時間）。五役の独立Codexセッションを、現在のホストのApp Serverで連携させる。実装・性能向上の研究は仮説、並列実験、批判、追加実験の循環で進める。

## 構成と判断

| 役割 | 継続して持つ文脈 | 判断・成果物 |
| --- | --- | --- |
| 研究統括 (`coordinator`) | 目標、仮説群、資源配分、採用判断 | 実験の選択・中止・追加、独立検証、製品統合の受入れ |
| 探索・仮説 (`hypothesis`) | 文献、代替案、競合仮説、失敗した方向 | 根拠・予想・反証条件・最小判別実験 |
| 実験 (`experiment`) | 試作、実行、計測、失敗原因 | 分離された実験と再現可能な結果 |
| 検証・批判 (`critic`) | 比較条件、再現・反証、交絡要因 | 主張の支持・不支持・保留と適用範囲 |
| 研究基盤・整理 (`steward`) | 環境、資源、成果物、保存と共通化 | 実行可否、競合回避、整理・共通化判断 |

共通方針は[common.md](../../.agents/research-team/common.md)、各役の指示は[roles/](../../.agents/research-team/roles/)に置く。この二つを結合してApp Serverの `thread/start.developerInstructions` に渡す。統括も独立スレッドとして作り、ユーザーと対話する準備チャットは別に保持する。モデル・effortは起動時のホスト設定を使用し、追加依頼と通知で上書きしない。

五役は役割の数であり、実験数や常時稼働人数ではない。必要な仕事がある時だけturnを開始する。初期は最大3役を同時に実行し、CPU/GPUジョブ数は別に調整する。サブエージェントは契約に許可した独立調査・実験・再現試験へ使い、役割指示と契約を渡す。

## 研究の進め方

性能評価、ルール・探索の高速化、PV、自己対局、学習を一列の工程として完了待ちにしない。複数の仮説を保持し、最小の判別実験を並行して進め、結果から追加の枝と中止条件を更新する。期待改善に加え、その実験によって何が分かるかを選定理由にする。

製品のRust/Wasm、value視点、Worker、モデル配布などの要件は[既存AI設計](quoridor-3d-webapp-design-rust-wasm-v1.md)を維持する。同設計の性能計測・小規模検証は、大量生成や採用に必要な根拠として扱う。研究順の変更は、大量生成・学習・モデル取得を自動的に開始する許可ではない。

共通の対照と測定条件を固定し、候補ごとの結果を記録する。固定探索量での速度、固定実時間での棋力、有効な学習局面/時間、メモリ・配布サイズを混同しない。大きい変更は要素を外した比較や独立再実行で原因を切り分ける。LLMによる順位付けは候補の選定に使い、性能や正しさの確定は実測と検証による。

## 目標に対する自律運用

ユーザーは到達目標と許可範囲・資源上限を委任し、統括が課題定義の責任を持つ。[目標契約](../../.agents/research-team/templates/goal-contract.md)を一度共有した後は、その範囲で統括が課題の作成、優先付け、並行実験、再検証、方向転換、整理と採否を判断する。通常の課題追加や実験のたびにユーザーの承認を求めない。目標・資源上限・製品方針の変更が必要な場合は具体案をユーザーへ提示する。

統括は報告を受け、目標達成と予算・停止条件を確認し、未達で実行可能な課題があれば担当へ次の契約を送る。報告を評するだけでturnを終えない。担当からの報告待ちは担当とissueを明確にして終了でき、報告により次の統括turnが起動する。基盤担当は実験開始・終了、競合・容量増加・再現失敗を契機に参加する。全員を常時稼働させる必要はない。

目標issueは研究全体の継続を管理し、個別実験は子issueで担当と受入れを管理する。完了した子issueの報告で継続を起動するときは、通信の `--issue` に進行中の目標issueを指定し、本文に実験issueを記す。目標と個別作業のpauseは送信前にも確認する。既存deferred/paused issueを黙って再開しない。

2026-10-01（日本時間）のユーザー合意により、最初の到達目標は「固定したSigmaQuoridorと同じ計算資源・思考時間で同等水準の強さを持ち、ブラウザで使えるRust/Wasm AI」に確定した。Ka・gorisanson・Titanium・Claustrophobia・Ishtar / Zero-Inkは参考比較とし、これらへの勝利を初回の達成条件にしない。実装研究の主要参考はClaustrophobiaとSigmaQuoridorを維持する。

Sigmaのcommit/release、モデルのハッシュ、探索設定、対象機材、CPU/GPU・スレッド数・メモリ・思考時間を対戦前に固定する。同等水準は「実用上Sigmaに劣らないこと（上回る場合を含む）」として、統括と検証担当が非劣性許容差・信頼水準・開始局面・先後入替・必要な精度と判定手順を事前に定義する。思考時間と数値基準は未確定で、従来の1手1秒案は採択済みの制約として扱わない。200対局程度は探索的な開始数であり、必要な精度が得られた保証とはしない。

研究用のnative/ローカル比較と製品Wasm版対Sigmaブラウザ版の比較は、それぞれ同じ機材と資源上限で実測する。nativeの成績でブラウザの棋力を代弁しない。計算資源を統制できない外部サービス対戦は参考結果として記録する。

ブラウザでの合法手、キャンセル、応答性、メモリ制約も同時に満たす。B0/B1、高速化、評価器、ソルバ、学習のどの枝を使うかは目標契約の許可範囲で統括が選ぶ。手法の導入自体を成功とせず、棋力と製品制約の達成を判定する。到達目標は確定したが、研究の累積資源予算・実行範囲は目標契約で設定する。目標設定の変更だけで既存deferred/paused作業を再開しない。

## 依頼と報告

[実験契約](../../.agents/research-team/templates/experiment-contract.md)に、問い・仮説・反証・対照・固定条件・予算・終了条件・書き込み担当・作業場所・再現方法を含める。[引き渡し](../../.agents/research-team/templates/handoff.md)で、実装失敗、実験不成立、negative resultを区別する。

作業の状態・担当・依存は[Beads](../development/beads-workflow.md)。設計と根拠は文書、測定と生データは実験成果物、起動と終了はホストの履歴に置く。実行registryは役割とスレッドID・定義ハッシュを対応付けるだけで、作業状態を複製しない。

報告元の役割は `CODEX_THREAD_ID` とregistryで確認する。報告はユーザーの承認・pause解除として扱わない。対象issueがblocked/deferred/closed、またはpaused-by-userなら追加依頼と報告によるturn起動を拒否する。共有DBへの操作はwrapperを通す。

App Serverから現在の状態を読み、idleなら `turn/start`、activeなら現在のturn IDを指定した `turn/steer` を使う。notLoadedなら設定の上書きなしで `thread/resume` する。通知は宛先の次のturnを起動できる。追加依頼は同じスレッドの研究文脈を継続する。

## 環境と整理

書き込み作業は管理worktreeで行い、一つの範囲の担当を一人に決める。依存環境・出力先を実験ごとに区別し、更新中の共有環境やCPU/GPU競合下で正式な性能比較をしない。長時間ジョブは実行プログラムがPID/ジョブID、ログ、チェックポイント、終了状態を保存する。

基盤担当は開始・終了・中止、依存衝突、容量増加、再現失敗を契機に点検する。実行中プロセス・成果物の参照を確認し、採用物、再現に必要な証拠、再生成できる一時物を区別する。許可された一時物だけを整理し、失敗の知見、小さなmanifest、必要なcheckpointを残す。[storage policy](../../.devcontainer/storage-policy.md)に従う。

## 用意するものと操作

`scripts/dev/research-team.sh` は既存App Serverへの単発クライアント。接続先を `codex app-server daemon version` から取得する。サーバーの起動・再起動、通知サービス、配送キューは追加しない。明示的な運用契約を持つ定期点検には、別の単一プロセスを使う。[スケジューラーの設定・運用手順](../development/research-scheduler.md)を参照する。スケジューラーの用意だけで監督セッションや定期運用を開始しない。既存Lead/Sidekickと同じUnix WebSocket経路を使う。この研究チームはLead/Sidekick Skillの自動起動を意味せず、そのSkillの再帰委譲禁止やモデルprofileを研究チームへ自動適用しない。

依存は `tools/research-team/pyproject.toml` と `uv.lock` に保持する。uv cacheと専用Python環境は既存inference-cacheへ置き、学習環境を変更しない。初回クライアント実行はlockfileから復元する。`QUORIDOR_RESEARCH_TEAM_ENV` に学習環境と同じパス（symlinkを含む）を指定すると起動を拒否する。通常の `uv run --locked` は専用環境を同期するため、依存準備済みの環境で読み取りのみの契約を実行する場合は `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1` を付ける。

```bash
# 現在のチャットと同じホストへの接続を確認
bash scripts/dev/research-team.sh diagnose

# ユーザーが許可したチーム準備issueで、五役の保存スレッドを作成
# 再実行は既存registryの同じスレッドを確認し、未作成の役割だけ補完する
bash scripts/dev/research-team.sh init --issue <setup-issue>
bash scripts/dev/research-team.sh status

# body-fileに実験契約全文を保存して送る
bash scripts/dev/research-team.sh send hypothesis --issue <task-issue> --body-file /absolute/path/contract.md

# 書き込み担当へ管理worktreeを指定して依頼
bash scripts/dev/research-team.sh send experiment --issue <task-issue> --cwd /workspaces/quoridor/.worktree/<name> --body-file /absolute/path/contract.md

# 各役のセッション自身が報告。idleの宛先も起動できる
bash scripts/dev/research-team.sh report --to coordinator --issue <task-issue> --body-file /absolute/path/handoff.md

# nativeイベントで待つ。最大50秒で呼出し側へ戻り、モデルturnは継続する
bash scripts/dev/research-team.sh wait experiment --timeout 45
bash scripts/dev/research-team.sh read experiment --limit 1

# 明示的な停止。実験プロセスの停止は契約の停止方法でも確認する
bash scripts/dev/research-team.sh interrupt experiment

# 役割指示を編集した後、idleの同じスレッドへ明示適用（モデル設定は保持）
bash scripts/dev/research-team.sh refresh critic --issue <task-issue>
```

registryは主checkoutの `.artifacts/research-team/registry.json`。これはローカル実行情報でGit対象外。別の検証チームは `--registry /absolute/path/registry.json` を指定する。registryを紛失した時はホスト履歴からスレッドを確認し、重複した実行を作らない。定義変更を検知したら追加依頼を止め、idleで明示refreshする。

初期化では各役に研究を行わない短い確認turnを与え、保存・再開できる履歴を作る。初期化が途中で止まった場合は保存スレッドを確認してから再実行する。サーバーが `no rollout found` と確認した未初期化スレッドに限り、`init --repair-empty --issue <setup-issue>` で対応付けを補修できる。履歴があるスレッドの置換や再作成には使わない。

五役のスレッド作成はチーム準備の範囲。研究の本作業には別のissueと実験契約を用意する。今回の導入結果と確認できた能力・制約は[検証報告](../reports/ai-research-team-setup.md)に記録する。

## 根拠

- [Codex App Server](https://learn.chatgpt.com/docs/app-server): thread/turn操作とnativeイベント。具体的なmethod・fieldは稼働中binaryの生成schemaと実応答で照合する。
- [Codex Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): 独立したサブエージェントと役割別指示。
- [AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/): 仮説生成・批判・改良。
- [AI Scientist-v2](https://arxiv.org/html/2504.08066v1): 分岐した並列実験、再実行、ablation。
- [AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/): 候補生成と実測による探索。

## 継続枠の監督運用

契約を含むチームの動き方の改善は、外から見るsupervisorが自律的に主導する。統括自身と既存契約も評価対象であり、ユーザーの指摘を待たず、矛盾・古い制約・手続き増殖・費用対効果を調べる。問題発見→最小改定案→統括の採否と担当調整→所有者による現行本文と保存指示の反映→監督の効果点検まで追う。許可済みの目標・期限・資源・製品範囲内の改善はチーム内で進める。ユーザー指定の上限変更や停止解除はこの委任に含まれない。統括との重大な見解差が解消されなければ、双方の根拠をユーザーへ報告する。監督の提案送信だけで改善完了にせず、監督自身が設定を書き換えたりworkerを起動したりもしない。

監督は研究運用の批判的評価を担い、統括の判断・課題選定・契約・検証手順も評価対象とする。criticは実装・結果の正しさと公平性を担う。担当稼働や局所的な原因発見だけで進展とせず、累積費用に対して目標検証に使える証拠が増えているかを見る。監督の提案へ統括が採否/理由/担当/確認時点を記録し、監督が効果と未回答を追う。問題が続けば不採用の案も再検討する。

デバッグは失敗と版/差分を残して許可枠内で修正・機能確認を反復し、最小の動作経路を固定して独立検証へ渡す。正式棋力評価の条件/標本/停止規則は事前固定し、デバッグ結果と成績を混ぜない。過去の単発窓を遡及延長せず、NN0のschema/設定検査を高価な試験の前に行う。監督にコード変更やworker起動の権限は追加せず、改善の適用は統括が書込所有者と調整する。

研究の再実行・記録は[AI研究の実行・再実行・記録](../development/ai-research-experiments.md)を正本とする。許可した総予算でデバッグ/再現/性能測定を反復し、正式評価の成績選別はしない。Git版/run/必要なログ結果で管理し、全コピー/全履歴hashを義務にしない。研究ローカルGit管理は可、製品main統合/push/公開と期限/予算拡張は不可。

現行の契約は[研究目標](ai-sigma-research-goal.md)（継続する目標）、[実行枠](ai-sigma-continuation-20261001.md)（現在の期限・上限）、担当契約（問い・所有・配分・必要検証）で役割を分ける。有効本文を直接更新し、旧禁止事項と補足を積み重ねて読み替えない。診断対局は最小条件から進め、正式認定の全手続きは[比較方法](ai-sigma-comparison-protocol.md)に分ける。

監督は現在の課題・担当・待ちを動的取得し、予算内の追加readonly確認と一時障害の有界再試行を行える。調査は不支持/失敗/未完了終了でも停止・必要記録後に完了できる。停止・受入れ済みなら統括が担当を引き継いでcloseし、専用LLM turnを増やさない。保存会計は保持実量と有効予約の未使用分を管理し、過去peakは別記する。次枠の計画だけでユーザーの終了時刻を延長しない。

「終了窓の再開」の禁止は、旧実行の期限・成績を遡及的に書き換えないという意味である。同じコード・入力・コマンドでも、現在の許可範囲と総予算内で新runとして再現確認できる。旧.80と同じ内容を新runで検証すること自体は禁止しない。進行中の具体的許可差分と残予算はcoordinatorが明示する。
