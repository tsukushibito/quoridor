# NNUE研究・現行実行枠

契約版20。ユーザー明示「利用枠制限で中断した。再開して。」を受け、前回明示の2時間を継承した新frame20を開始する。開始2026-10-05 00:51:02 UTC / 09:51:02 JST、終了02:51:02 UTC / 11:51:02 JST。準備完了から起点を取り直さない。旧frame19の終了00:52:46、各科学runの期限・結果・欠測・usageLimitExceeded失敗・累積課金と運用停止証拠はGit/既runで保持し遡及変更しない。最終目標は[研究目標](ai-sigma-research-goal.md)のNNUE型Quoridor AIの最高棋力であり、未達のまま継続する。中断箇所の安全復旧と、NNUE教師精度の利益を同時間棋力へ接続する評価器経路、探索費を削減する探索経路を主問いとする。具体案・数量・順序・担当・総予算・採否は統括とチームへ委任し、通常root再承認を開始gateにしない。

## 期限と資源

| 項目 | 現在の上限・運用 |
| --- | --- |
| 開始 | 2026-10-05 09:51:02 JST / 2026-10-05 00:51:02 UTC |
| 終了 | **2026-10-05 11:51:02 JST / 02:51:02 UTC**（新枠2時間） |
| 新しい重いjob | 2026-10-05 11:41:02 JST / 02:41:02 UTCまで。保存・回収が枠内に収まる時だけ開始 |
| 監督停止 | 2026-10-05 11:46:02 JST / 02:46:02 UTC |
| monitor回収 | 2026-10-05 11:49:02 JST / 02:49:02 UTC |
| CPU | 計算job合計最大4論理CPU。CPU番号と使用数を分ける |
| RAM | 研究プロセス合計8GiB。current RSSと過去peakを分ける |
| LLM | 既saved6role＋rootの必要な依頼・報告・監督をactive数で拒否しない。同役二重起動を防ぐ |
| 保存 | 保持物・依存・cache・一時物＋有効予約の未使用分で12GiB以内 |
| GPU推論 | VRAM6GiB、1job30分。競合・所有を確認して統括が配分 |
| GPU学習 | 既承認累積2時間の確認済み未使用残だけ。旧残不明なら追加GPU学習0、CPU等で前進し累積上限を増やさない |

ユーザーpause、期限、資源上限、所有不明・回収不能で該当jobを停止する。必要な結果と子process終了を保存し、自動延長しない。次枠提案・報告到着は終了後の実行許可やpause解除ではない。既saved/model/effort/cwd・共有App Serverを維持する。

## 現在の問いと自律配分

240の同仕事量NNUE約54.38%/距離評価約65.14%短縮と、WDL/UNKNOWN・競合・単一component因果の限界を保持する。現在242 paired同wall診断、244の距離clip/tanh由来候補、保存済243静的案と中断箇所・exact child/backgroundjob/書込停止・既保存を確認し、通常復旧又は現配分の新runへつなぐ。完了部分を消さず、旧失敗・未知・未実施を成功補充しない。229旧final NOT_RUNや小対局未認定を維持する。

二経路で判断を進める。評価器側は同探索でNNUEと距離評価を比較する。探索側は同評価器で基本的な順序付け・置換表・合法生成/距離/clone/eval/control等の支配費を測定し、必要な私有薄改修と比較を行う。方策の利用はorderingのみ・全合法手を維持・計算費込みの候補であり、基本的な順序付けより先行させる固定義務ではない。全候補の実装完了を対局開始の前提にしない。

固定仕事量の測定は速度や原因の判別へ、同資源・同時間の探索的native対局は採否や棋力へ使う。depth、nodes/s、教師誤差だけで強さを認定しない。モデルと探索の版、比較対象・入力/時計・全attempt/未確認/合法性/費用/停止と必要な結果を保存する。通常診断と正式認定を分け、条件・終了規則を結果前に固定する。

既目標内の私有実装修復/高速化測定、必要なCPU学習・生成・独立test・探索的native対局まで許可するが、具体の問い/owner/編集範囲/総費用/必要検証/終了は統括がBeadsで配分する。同NIや追加学習の自動反復要求ではない。独立scopeで並行できる仕事は必要に応じて配分し、役割名で実作業を一人に固定しない。現物のCPU/RAM/保存・計測競合・編集所有を調整する。長時間jobは230の既背景実行・Idle→完了通知を再用でき、意味のないLLMpollingを増やさない。

重要な未解決点、保存済み証拠で答えられること、競合案より今優先する理由を既存計画・issueへ短く残す。原因分析と効果確認、個別実験の妥当性と配分全体の優先順位を分ける。hypothesis/criticの独立見解を必要な範囲で使い、保留案の理由と再検討契機を残す。supervisorは評価調整偏重・探索遅延放置・速度だけの成果、異論の採否/実配分/後続効果と節目の費用成果を外部点検する。新会議・台帳・全役承認・全履歴再集計を義務にしない。

## 評価・保存・編集の境界

既存train/validationを探索的な調整に使え、選定と最終評価を区別する。開封済みtestを設定選択に戻さず、173正式198局は非学習。旧成績・分割・mask・候補固定の履歴を保持する。必要な独立評価のデータと条件は結果前に固定し、選定に戻した結果を未見評価にしない。小調整ごとに独立test一式を一律要求せず、判断に必要な節目で行う。

native/localを主評価とし、ブラウザの必要動作は別結果にする。正式棋力は[比較方法](ai-sigma-comparison-protocol.md)に従い相手・条件・分布・失敗・終了・統計規則を結果前に固定する。速度・教師量・接続成功・予測利益・同時間棋力を区別し、旧173の不確かと正式成績を新診断へ混合しない。

コード・設計・必要な実験検証データは研究Git、状態・所有・依存はBeads wrapper。版/run/入力参照/再現command/実費/結果/欠測/停止を残し、全sourceコピー・毎run新issueを増やさない。保持実量と有効予約の未使用分を分け、予約内実量を二重計上せず、旧予約・累積をresetしない。確認済み未使用だけ移動/返却でき、過去peakを永久課金せず未知量を減額しない。詳細は[実行と記録](../development/ai-research-experiments.md)。

親main/mirrorと92運用sourceのsole writerはsteward。root/coordinatorは同sourceへ書込・重複起動依頼をしない。研究sourceは統括が現在所有と停止を確認して配分し、必要main mirrorはstewardが停止hashを受けて同期する。他者の未コミット作業・indexを保持する。新モデル取得・共有依存/toolchain更新、有料クラウド・製品統合/push/公開・未知削除は追加許可しない。[保存方針](../../.devcontainer/storage-policy.md)と既目標を継承する。

## 再開と監督運用

92は旧frame19 scheduler/monitorの正確identity不在・owned停止・monitor-endedを必要範囲で確認し、新frame20の絶対期限・現common/6role・registrydigest/24期待inputSHAへ束縛する。旧科学・欠測・失敗・運用gapを新successへ変更しない。旧00:21:13 fatal_dispatch_error usageLimitExceededと最新監督failedを保持する。新turnに再発したら実エラーを保存停止し、盲目retry・強制tick・モデル変更・AppServer再起動で迂回しない。旧運用全史やACK待ちを研究静的開始gateにしない。heavyは各ownerが現物資源・正currentbinding/owned/pauseとquiet・測定競合を確認して開始する。

period1200/max_turn_seconds=null、CPU0単1/RAM1GiB・既112MiB guard/保存予約内のcurrent+forecastを維持する。同役二重開始/dispatch lock/所有/pause/通信応答不明保護/自己子process回収/運用endで正確ownedだけ回収を維持し、他active数で拒否せず、強制tick・他owner interrupt・AppServer再起動・設定変更をしない。promptの研究判断は現supervisor定義を参照し役全文・旧診断手順を複写しない。正常毎周期通知を義務にせず、重要な改善・節目・障害・異論と必要行動だけ通知する。

停止窓でsource/bindingを固定→validate→正常既helperの通常freshstart→実running/configcontractloaded値SHA/正PIDtickboot/24期待hash/6digestを確認する。必要な最小静的修復は同scope/総費内で行え、新helper/全面改定を義務にしない。起動受理・実loaded・自然点検成果・未来全期間成功を区別する。92は2026-10-05 02:41:02新heavy停止通知、02:46:02監督scheduler+正owned停止、02:49:02monitor回収、02:51:02最終保存を長期所有する。外部NN停止は各研究ownerが別に確認し、自己停止から認定しない。必要証拠・Git・Beads append-notes/backupを保存する。
