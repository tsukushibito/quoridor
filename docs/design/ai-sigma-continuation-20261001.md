# NNUE研究・現行実行枠

契約版23。ユーザーの明示「8時間追加」をframe22の連続延長として適用する。開始2026-10-05 11:36:03 UTC / 20:36:03 JSTを維持し、従来の終了15:36:03 UTCへ8時間を追加して23:36:03 UTC / 翌08:36:03 JST終了（開始から計12時間）とする。追加受領や準備完了から時計を取り直さない。旧運用期限・停止証拠はGit/既runに保持し、終了済み科学runの結果・失敗・個別期限・累積費用は遡及変更しない。科学の新配分と既runの延長を区別する。最終目標は[研究目標](ai-sigma-research-goal.md)のNNUE型Quoridor AIの最高棋力であり未達。Sigma同等は段階目標・比較基準である。

## 期限と資源

| 項目                         | 現在の上限・運用                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| 開始                         | 2026-10-05 11:36:03 UTC / 20:36:03 JST                                                 |
| 終了・必要保存               | **2026-10-05 23:36:03 UTC / 翌08:36:03 JST**                                           |
| 新heavy開始停止              | 23:26:03 UTC / 翌08:26:03 JST。保存・回収が枠内に収まる時だけ開始                      |
| 監督scheduler・正確owned回収 | 23:31:03 UTC / 翌08:31:03 JST                                                          |
| monitor回収                  | 23:34:03 UTC / 翌08:34:03 JST                                                          |
| CPU                          | 研究合計最大4論理CPU。CPU番号と使用数を分ける                                          |
| RAM                          | 研究プロセス合計8GiB。current RSSと過去peakを分ける                                    |
| 保存                         | 現保持物・依存・cache・一時物＋有効予約未使用分で12GiB以内                             |
| GPU推論                      | VRAM6GiB、1job30分。所有・競合を確認して統括が配分                                     |
| GPU学習                      | 既承認累積2時間の確認済み未使用残だけ。残不明なら追加GPU学習0                          |
| LLM                          | 既saved6role＋rootの必要な依頼・報告・監督をactive人数で拒否しない。同役二重起動を防ぐ |
| 運用管理                     | 1論理CPU、current RSS1GiB、GPU0。92既112MiB枠をcurrent＋forecastで確認しresetしない    |

ユーザーpause、期限、資源上限、所有不明・回収不能で該当jobを停止する。自動延長しない。報告到着・次枠計画・役割定義は研究再開やpause解除の許可ではない。同saved/model/effort/settings・共有App Serverを維持する。

## 現在の問いと自律配分

主問いは、期待されるNNUE学習利益が棋力に現れていない原因。距離評価を上回る特徴・学習設計を目指し、自動的な理論保証と実証を区別する。QF1は二視点の各312疎入力と駒位置distance2であり、全mapを入力した表現ではない。教師精度・特徴表現・学習尺度・探索での評価利用・分布と同時間探索費などの競合説明を、既知の根拠と現在の実装・実測から選ぶ。特定説明を結果前に確定しない。

課題集合は[NNUE改善候補](ai-nnue-optimization-agenda.md)を唯一の一覧とし、探索速度・評価学習・教師生成の期待効果、情報価値、全工程費用を比較する。小不支持・不成立・不足教師/学習を方式全体の否定にしない。具体の問い・実装・数量・順序・担当・編集範囲・総予算・採否・必要検証を統括とチームへ委任する。許可内の生成、有限CPU学習・validation、必要な独立test、native診断・同時間対局、探索高速化・修復を通常配分できる。一律の全案実施・追加承認・全役ACK・全史検査を入口にせず、独立な静的研究は92準備完了を待たない。

固定仕事量の速度、教師誤差、同資源・同時間の棋力を分ける。depthやnodes/s、正常実行、学習接続だけで強さを認定しない。既存train/validationでの探索的選定と未見評価を区別し、開封済みtestを設定選択へ戻さない。173正式198局は非学習。正式評価は[比較方法](ai-sigma-comparison-protocol.md)に従い対象版・資源・時計・入力分布・全attempt/失敗・集計・終了規則を結果前に固定する。native/localとbrowserの到達証明を混同しない。

## 正本・所有・保存

mainが持続的研究の統合正本。現役のRust/Pythonと`tools/research-team`・`scripts/dev`を利用し、旧Node/旧学習recipe・廃止経路を復活させない。旧checkoutsは保全・復元確認後に撤去済み。必要モデル・checkpoint・入力は`.worktree/assets/{models,checkpoints,inputs}`へ分類し、`research-paths.json` v2と`research-assets.py`で現在path/SHAを解決する。役割・文書・現役sourceの恒常mirrorを作らない。frame21-search/featuresは具体比較用途の保存sourcepointとして保護する。親本文と92運用source/currentbindingのsole writerはsteward92。root/coordinatorは重複編集・起動しない。科学sourceは各課題の単独ownerが扱う。

コード・必要なデータ/証拠はGit、所有・状態・依存はBeads wrapper。版/run/入力参照/再現command/実費/結果/欠測/停止を残す。Git index/commitは統括の単一統合ownerが全writer停止点で通常indexを扱う。92は変更pathと停止を引き渡しprivate indexによるHEAD更新を行わない。同時rootのGit操作があれば先に調整する。旧保持未知量を減額せず、予約内実量を二重計上せず、確認済み未使用だけ再利用/移転する。新モデル/依存取得・共有環境更新・公開/push・未知削除は追加許可しない。

## 再開・点検・回収

92は旧正確PID/starttick/boot不在、owned停止、旧monitor-endedとstate/errorを必要少数で確認・保存し、新期限・親hash・現common/6role digest・24期待inputへbindする。旧失敗と新usageLimitExceededをexactturn/dispatch receiptから区別する。実新usage再発は保存停止、盲目retry・force tick・モデルeffort変更・サーバー再起動0。停止窓でsourceを固定しvalidate→通常freshstart→実running/loaded config-contract SHA/現在inputhash/正2identity/最初ownedを確認する。freshstartをreloadedと呼ばない。運用受理・実loaded・自然監督品質・科学成功・未来停止保証を分ける。

period1200/max_turn_seconds=nullを維持する。正owned activeなら次周期は二重開始せず、180秒elapsedだけでinterruptしない。pause・運用endで正確ownedだけ回収、他者turn保護・dispatch lock・通信timeout・子回収・有界RSS/保存guardを維持する。物理admissionは現在CPU/RAM/GPU/tool競合によって判断し、LLM人数やowned非nullをCPU占有の代用にしない。promptの研究判断は現supervisor定義と唯一の課題集合を参照し、集中・機会損失・早期断念・各役の実働と監督自身の改善効果を点検する。統括は23:00 UTC頃までに既自然報告の終了振り返りとしての十分性を判断し、不足だけを同枠内へ実配分する。遅い新turnや未完了回収を期限成功へ付替えない。意味のある改善・節目・障害だけ通知し正常周期通知を増やさない。

92が23:26:03通知、23:31:03正owned/scheduler停止、23:34:03monitor回収、23:36:03必要証拠保存を所有する。終了準備の既通知に合わせ、枠内で停止・保存と整理/長期保守要否を実判断する。現役構成と利用のずれ、未追跡/共有cache/入力の保護、小整理候補の実施又は保留理由/再検討契機を既reportへ返す。通知送信やprogram停止だけで判断完了としない。許可外の整理は候補だけ示す。時間・根拠不足は確認範囲・未完了理由・担当・次機会を引き渡し、枠外作業で救済しない。外部NN停止は各科学ownerが別に確認する。必要Beads append-notes/backupを保存する。

延長後の重要選定では現hypothesis/coordinator/supervisor定義に従い、重要候補を見積もり不足だけで保留せず、必要規模・総費用・期待効果と情報価値の概算を配分へつなぐ。厳密な見積もり完成や小規模候補の成功を一律の入口にしない。旧14:27終了保守判断は保存済みとして再用し、新しい保持増加・採用・読者終了の変化だけを次の点検へ反映する。
