# Quoridor AI研究チーム

決定日: 2026-10-01（日本時間）。五つの研究役と独立した運用監督を、既存の保存CodexセッションとApp Serverで連携させる。実装・性能向上の研究は仮説、並列実験、批判、追加実験の循環で進める。

## 構成と判断

| 役割 | 継続して持つ文脈 | 判断・成果物 |
| --- | --- | --- |
| 研究統括 (`coordinator`) | 目標、重要な不確実性、仮説群、資源配分 | 次判断に使える実験の選択・中止・追加、独立見解の配分、採用判断 |
| 探索・仮説 (`hypothesis`) | 文献、問いと評価の前提、競合仮説、失敗した方向 | 問い・実装・評価の代替案、反証条件・最小判別実験 |
| 実験 (`experiment`) | 試作、実行、計測、失敗原因 | 分離された実験と再現可能な結果 |
| 検証・批判 (`critic`) | 評価設計、比較条件、再現・反証、交絡要因 | 差を見分けられる設計か、主張の支持・不支持・保留と改善案 |
| 研究基盤・整理 (`steward`) | 環境、資源、成果物、保存と共通化 | 実行可否、競合回避、整理・共通化判断 |
| 運用監督 (`supervisor`) | 選定理由、重要な保留案、累積費用、改善追跡 | 独立した方針評価、再検討提案、適用後の効果確認 |

共通方針は[common.md](../../.agents/research-team/common.md)、各役の指示は[roles/](../../.agents/research-team/roles/)に置く。この二つを結合してApp Serverの `thread/start.developerInstructions` に渡す。統括も独立スレッドとして作り、ユーザーと対話する準備チャットは別に保持する。モデル・effortは起動時のホスト設定を使用し、追加依頼と通知で上書きしない。

五役は役割の数であり、実験数や常時稼働人数ではない。必要な仕事がある時だけturnを開始する。既saved6role＋rootの必要な依頼・報告・監督をactive数で止めず、CPU/GPU・RAM・保存の実資源配分は別に調整する。サブエージェントは契約に許可した独立調査・実験・再現試験へ使い、役割指示と契約を渡す。

## 研究の進め方

性能評価、ルール・探索の高速化、PV、自己対局、学習を一列の工程として完了待ちにしない。複数の仮説を保持し、最小の判別実験を並行して進め、結果から追加の枝と中止条件を更新する。期待改善に加え、その実験によって何が分かるかを選定理由にする。

各役は目標から問いを捉え、観測・解釈・仮説を区別する。既知の方法と競合説明を照合し、低費用診断・少数条件比較・方式変更・最終評価から次の判断に使える方法を選ぶ。定石は判断材料として使い、特定の手順や一律の順序を義務にしない。

統括は次の配分で、目標への最大の未解決点、保存済み証拠で答えられること、競合案より判断を進める理由を現在計画・既存issueへ短く残す。原因を区別する分析と効果を確認する評価を混同せず、個別実験の妥当性と候補全体の優先順位を分ける。意味のある結果で主計画を更新し、有力な代替案の見送り理由と再検討契機を残す。hypothesisは競合説明と判別案、criticは実行前の問い・観測の妥当性と実行後の主張、supervisorは選定全体の偏りと費用対効果・保留案の追跡を担う。役割名は実行担当を固定せず、必要な仕事と所有・資源で配分する。毎回の全役承認や新しい台帳を設けない。

一課題で複数の対照条件・反復を総予算内にまとめられる。探索的な診断・調整は必要な観測から条件を見直し、最終評価は候補・条件・データ・終了規則を結果前に固定する。小さな調整ごとに最終評価一式を要求せず、選定に使った結果を未見評価に戻さない。正常実行や正式認定保留だけで価値を判断せず、改定の効果は未指摘の問題が判断・配分・成果の改善につながった実績で見る。

製品のRust/Wasm、value視点、Worker、モデル配布などの要件は[既存AI設計](quoridor-3d-webapp-design-rust-wasm-v1.md)を維持する。同設計の性能計測・小規模検証は、大量生成や採用に必要な根拠として扱う。研究順の変更は、大量生成・学習・モデル取得を自動的に開始する許可ではない。

共通の対照と測定条件を固定し、候補ごとの結果を記録する。固定探索量での速度、固定実時間での棋力、有効な学習局面/時間、メモリ・配布サイズを混同しない。大きい変更は要素を外した比較や独立再実行で原因を切り分ける。LLMによる順位付けは候補の選定に使い、性能や正しさの確定は実測と検証による。

## 目標に対する自律運用

ユーザーは到達目標と許可範囲・資源上限を委任し、統括が課題定義の責任を持つ。[目標契約](../../.agents/research-team/templates/goal-contract.md)を一度共有した後は、その範囲で統括が課題の作成、優先付け、並行実験、再検証、方向転換、整理と採否を判断する。通常の課題追加や実験のたびにユーザーの承認を求めない。目標・資源上限・製品方針の変更が必要な場合は具体案をユーザーへ提示する。

統括は報告を受け、目標達成と予算・停止条件を確認し、未達で実行可能な課題があれば担当へ次の契約を送る。報告を評するだけでturnを終えない。担当からの報告待ちは担当とissueを明確にして終了でき、報告により次の統括turnが起動する。基盤担当は実験開始・終了、競合・容量増加・再現失敗を契機に参加する。全員を常時稼働させる必要はない。

目標issueは研究全体の継続を管理し、個別実験は子issueで担当と受入れを管理する。完了した子issueの報告で継続を起動するときは、通信の `--issue` に進行中の目標issueを指定し、本文に実験issueを記す。目標と個別作業のpauseは送信前にも確認する。既存deferred/paused issueを黙って再開しない。

2026-10-03のユーザー指示により、最終目標は「NNUE型で最強のQuoridor AI」とする。[研究目標](ai-sigma-research-goal.md)と[NNUE研究方針](ai-nnue-research.md)を参照し、統括・仮説・検証・監督は課題選定をこの目標への貢献から判断する。最初の到達目標は、固定したSigmaQuoridorと同じ計算資源・思考時間で同等水準の強さを持ち、ブラウザで使えるRust/Wasm AI。Sigmaモデルを使う忠実な探索、自前モデルの学習、NNUE＋αβ比較を基本経路とするが、必要な予備調査と並行実験は枠内で配分できる。Ka・gorisanson・Titanium・Claustrophobia・Ishtar / Zero-Inkは初回には参考比較、最終段階では有力AIから正式比較対象を選ぶ。これらへの勝利を初回の達成条件にしない。実装研究の主要参考はClaustrophobiaとSigmaQuoridorを維持する。

Sigmaのcommit/release、モデルのハッシュ、探索設定、対象機材、CPU/GPU・スレッド数・メモリ・思考時間を対戦前に固定する。同等水準は「実用上Sigmaに劣らないこと（上回る場合を含む）」として、統括と検証担当が非劣性許容差・信頼水準・開始局面・先後入替・必要な精度と判定手順を事前に定義する。思考時間と数値基準は未確定で、従来の1手1秒案は採択済みの制約として扱わない。200対局程度は探索的な開始数であり、必要な精度が得られた保証とはしない。

棋力評価・大量対局・自己対局はネイティブを主環境とする。[研究目標](ai-sigma-research-goal.md)の方針に従い、Wasmは必要な互換性・製品動作・少数実用確認へ絞る。大規模Wasm評価をネイティブ研究の入口条件にせず、必要なブラウザ正式評価は別の範囲・後段として定義する。比較する両AIの資源・思考時間を揃え、参照の版・探索規則・実行バックエンドを明示する。nativeの成績でブラウザの棋力を代弁しない。計算資源を統制できない外部サービス対戦は参考結果として記録する。

統括と各担当は高速化・効率化を重視し、対局数／時間、有効学習局面数／時間、結果取得までの総時間と棋力から実験・実装の費用対効果を判断する。監督は節目にその改善が目標への前進へつながったかを点検する。測定項目の全実施や新しい承認層を一律の開始条件にしない。

ブラウザでの合法手、キャンセル、応答性、メモリ制約も同時に満たす。B0/B1、高速化、評価器、ソルバ、学習のどの枝を使うかは目標契約の許可範囲で統括が選ぶ。手法の導入自体を成功とせず、棋力と製品制約の達成を判定する。到達目標は確定したが、研究の累積資源予算・実行範囲は目標契約で設定する。目標設定の変更だけで既存deferred/paused作業を再開しない。

## 依頼と報告

[実験契約](../../.agents/research-team/templates/experiment-contract.md)に、問い・仮説・反証・対照・固定条件・予算・終了条件・書き込み担当・作業場所・再現方法を含める。[引き渡し](../../.agents/research-team/templates/handoff.md)で、実装失敗、実験不成立、negative resultを区別する。

作業の状態・担当・依存は[Beads](../development/beads-workflow.md)。設計と根拠は文書、測定と生データは実験成果物、起動と終了はホストの履歴に置く。実行registryは役割とスレッドID・定義ハッシュを対応付けるだけで、作業状態を複製しない。

報告元の役割は `CODEX_THREAD_ID` とregistryで確認する。報告はユーザーの承認・pause解除として扱わない。対象issueがblocked/deferred/closed、またはpaused-by-userなら追加依頼と報告によるturn起動を拒否する。共有DBへの操作はwrapperを通す。

App Serverから現在の状態を読み、idleなら `turn/start`、activeなら現在のturn IDを指定した `turn/steer` を使う。notLoadedなら設定の上書きなしで `thread/resume` する。通知は宛先の次のturnを起動できる。追加依頼は同じスレッドの研究文脈を継続する。

## 環境と整理

書き込み作業は管理worktreeで行い、一つの範囲の担当を一人に決める。依存環境・出力先を実験ごとに区別し、更新中の共有環境やCPU/GPU競合下で正式な性能比較をしない。長時間ジョブは実行プログラムがPID/ジョブID、ログ、チェックポイント、終了状態を保存する。

基盤担当は研究枠の終了・再利用、重複や容量の増加、依存衝突、再現失敗などの節目で、整理の必要性を必ず判断する。前回以降の変化を中心に、開発・検証・保存の総費用から実施の範囲・担当・時期、または見送り理由と再検討の契機を既存issue・報告へ短く残す。整理の実施量を成果指標にせず、毎runの全体監査・整理実施・追加の定期呼出しを義務にしない。実施時は実行中プロセス・成果物の参照を確認し、採用物、再現に必要な証拠、再生成できる一時物を区別する。許可された一時物だけを整理し、失敗の知見、小さなmanifest、必要なcheckpointを残す。[storage policy](../../.devcontainer/storage-policy.md)に従う。

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

監督は現課題・担当・待ちを動的に調べ、目標への成果と累積費用から節目を判断する。重要な提案の採否・保留理由・再検討条件・未回答を追い、条件が変わった、情報が増えない、判断の根拠が弱い場合に再検討を求める。統括自身の判断と既存契約も対象にし、統括の説明や役割間の一致を追認の根拠にしない。

改善は問題と最小変更の提案→統括の採否・担当調整→所有者の適用→後続の効果確認まで追う。重要な見解差が解消しなければ双方の根拠をユーザーへ示す。監督自身も評価対象とするが、追加監督・毎課題の会議・相互承認・全履歴集計は義務にしない。監督到着を研究開始のgateにせず、通常の改善は委任範囲で進める。

役割定義は `.agents/research-team/` を正本とし、数値・周期・issue・回収方法・guard commandは現在の運用契約とpromptに置く。promptの研究判断は現行supervisor roleを参照し、旧本文を複写して追加指示で読み替えない。変更を保存セッションへ反映し、運用中なら所有者が秩序ある停止とbinding更新を扱う。終了済みのconfigや停止証拠を遡及更新せず、次の許可枠の開始前に現行定義と期限を束縛する。

監督は観測専用で他役のコード・契約・設定を編集せず、workerや実験を起動しない。自己toolとowned turnの回収は現運用契約の時計・予算で行う。通知や次枠提案から研究再開・pause解除・期限延長を推定しない。

現契約は[研究目標](ai-sigma-research-goal.md)、[実行枠](ai-sigma-continuation-20261001.md)、担当契約へ責任を分ける。有効本文を直接更新し、旧規約と補足を積み重ねない。再実行と記録は[実行と記録](../development/ai-research-experiments.md)、正式棋力評価は[比較方法](ai-sigma-comparison-protocol.md)を参照する。旧実行の期限・成績を改変せず、現在の許可と総予算内なら同じコード・入力の新run再現を行える。

ユーザーの質問・指示とエージェント報告が同じturnに来ても未回答と採否を保持する。直接会話を制限せず、影響する指示を統括・所有者へ整合させ、報告だけで質問回答を置き換えない。
