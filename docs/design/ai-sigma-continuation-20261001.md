# NNUE研究・現行実行枠

契約版25（frame24連続extension25）。ユーザー01:24:53Z明示2時間追加、全期間4時間。開始2026-10-06T00:08:46Z（09:08:46 JST）固定、終了04:08:46Z（13:08:46 JST）。準備完了から起点を取り直さない。前frame23の期限・停止・失敗・成績・累積費・UNKNOWN・保存原本は変更しない。最終目標は[研究目標](ai-sigma-research-goal.md)のNNUE型Quoridor AIの最高棋力であり未達。

## 期限と資源

| 項目                             | 有効契約                                                                                                                                                                                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 開始                             | 2026-10-06T00:08:46Z固定                                                                                                                                                                                                                                |
| 終了・必要保存                   | 2026-10-06T04:08:46Z                                                                                                                                                                                                                                    |
| 新heavy開始停止                  | 03:58:46Z。回収・保存まで枠内に収まるentryのみ                                                                                                                                                                                                          |
| Supervisor正owned＋scheduler終了 | 04:03:46Z                                                                                                                                                                                                                                               |
| monitor回収                      | 04:06:46Z                                                                                                                                                                                                                                               |
| 終了点検                         | 03:40までに既依頼・現在証拠から判断し、未完了は担当・次機会を残す                                                                                                                                                                                       |
| CPU/RAM                          | 研究aggregate4logical/current8GiB。運用1logical/current1GiBも内数                                                                                                                                                                                       |
| 保存                             | 現保持・依存・cache・temp＋有効unused12GiB、UNKNOWN全額保持                                                                                                                                                                                             |
| GPU推論                          | VRAM6GiB、1job30分、各ownerが現競合・実費を確認                                                                                                                                                                                                         |
| GPU学習                          | 旧承認累積7200秒のUNKNOWN/費は保持。2026-10-06T00:32:01Zのユーザー新明示3600秒を別namespaceへ前向き配分、init/転送/fit/validation/同期/保存/回収・失敗込み累積。旧残復元を新許可のgateにしない。VRAM6GiB/job30分・親固定終了とfresh保存/物理/所有を守る |
| 運用保存                         | 92既112MiBをcurrent＋forecastで確認、resetしない                                                                                                                                                                                                        |
| 定期運用                         | period1200/max_turn_seconds=null。人数gateなし・正owned/同役二重開始なし                                                                                                                                                                                |

pause・期限・資源上限・所有不明・回収不能を尊重し、自動延長しない。同saved/model/effort/cwd/settings維持、共有App Server再起動・強制tickなし。新モデル/依存取得・環境更新・外部公開/push・未知削除は許可しない。

## 今枠の問いと配分境界

主目的は現在の学習を正確に診断すること。観測前にarchitecture・教師・data scale・samplingを変更しない。重要な方法・特徴・データ変更はRoot/ユーザーへの具体提案とし、通常修復・同条件観測・correctness検証は許可する。課題集合は[NNUE改善候補](ai-nnue-optimization-agenda.md)を唯一の一覧とし、現在の観測・未解決・全費と代替案を比較する。小不支持/未成立/不足学習を方式全体否定にしない。

308 Hypothesisは現canonical trainerの観測・中断・earlystop・selected exposure・CLI checkpointを単独担当し、sampler/model/math手法を変えない。Experimentは保存298/302を独立分析し、修復後の旧sampler/LR/corpusと同条件dense観測へ接続する。Criticはframe21-search比較専用TTfunctionalを扱い、main prototype未採用と保全pack5dfaを区別する。GPU比較は確認済み累積残を得て同batch CPU/CUDAを早期に観測し、大batchは別の重要提案とする。強さ・MSE・処理速度・depth・正常完了を相互代用しない。173正式198局は非学習、開封評価を設定選択へ戻さない。

具体課題のsource/owner/roots・inclusive forecast・科学全費/MAX・終了をBeads契約へ定める。304 data12MiBから3052/MPC.25を分離したretained9.75のうち、旧保全.25と確認unused9.5の3081.25/独立分析.25/TT2/dense観測・GPU小出力6MiB案は、実ownerの保全と受入れ・各exactroot/forecast成立後のみ有効とする。wholeheadroomを新配分とみなさない。旧304science2m/MAX2は別の明示unused移譲が成立するまで保持する。科学heavyはfresh storage/currentloaded/inputSHA・CPU/RSS/GPU・予算・所有・pauseを各ownerがentryで確認する。静的研究をops/全史/全roleACK待ちにしない。

## 正本・保存・運用

main /workspaces/quoridorを正本とし現役Rust/Python/scripts/dev/tools/research-teamを使う。必要model/checkpoint/inputは永続.worktree/assetsとroot research-paths.json v2/scripts/dev/research-assets.pyで解決し、実path/SHAを記録する。旧WT/Node/trainer復活・恒常mirrorなし。現在managed WTは具体比較/並行sourceとして保護する。親有効本文・運用registry/config/contract/prompt/期待hashのsolewriterは92、科学sourceは各契約の単独owner。全変更コードは担当範囲formatter/checkを行う。

Git通常index/commitは統括だけ。92は停止path/SHAを明示引渡し、privateindex HEAD更新なし。旧source20dcbc・旧state/deadline/errorsは元runへ保持し、旧正2identity/owned停止とSupervisor公式idleを必要少数確認して自然Supervisor idle/ownedなし・現在科学読者停止を確認して、旧frame24 stateを保持し新frame24-extension25別stateへ通常freshstartする。現common/6role digest・24inputSHAを固定→validate→start→実runningloaded/configcontractSHA/正PIDtickbootを確認する。oldfatalを新usage失敗へ付替えず、実newturn失敗は正dispatch receiptで区別し保存停止、盲目retryなし。

自然監督は現役Supervisor定義を参照し、学習診断の不足・重要変更の配分境界・集中/機会損失・役実働を点検する。正常周期全報告/全員採点・新層なし。終了振返りは直近報告を再用し不足だけ統括が枠内依頼する。92は03:58:46通知/04:03:46正owned scheduler/04:06:46monitor/04:08:46必要保存を所有し、03:40までに停止保存と整理・長期保守要否を実判断する。program停止や通知のみを判断完了としない。科学reader/子waitは各ownerの点証拠、外NN停止と運用終了を分ける。時間/根拠不足は理由・担当・次の明示機会を残し、Beads notes/backupと通常Git保存へ引渡す。92/親goalはcloseしない。

2026-10-06T00:32:01Zユーザー新許可: GPU学習3600秒をframe24-new-GPU-training-3600別namespaceへ前向き配分。Root正本 .artifacts/research-team/frame24-root/gpu-one-hour-authorized.md を参照し、旧7200秒UNKNOWN/原attempt/失敗は保持する。旧残復元を新許可のgateにしない。初比較は同corpus/初期/model/FP32/optimizer/旧game sampler/同batch128 CPU対CUDA512step、必要NN300k/MAX2を確認unusedから別束縛、個別hard300秒以内。init/転送/fit/validation/同期/記録/回収・失敗込み累積3600秒と親終了の早い方まで、VRAM6GiB/推論非競合/CPU4/RAM8GiB/保存12GiBを維持する。時間を使い切る義務や自動追加、大batch/方法変更の許可ではない。source308記録資格・同条件source固定、実output/Git/temp/原model保護・NN/MAX・累積残・物理を担当entryで確認する。

## extension25の連続性

ユーザー許可の正本は .artifacts/research-team/frame24-root/extension25-authorized.md（2026-10-06T01:24:53Z）。開始2026-10-06T00:08:46Zを維持する。新GPU3600秒は同namespaceの累積を継続し、foundation全attempt消費13.493288946秒・残3586.506711054秒の現在観測を引き継ぐ。旧7200秒UNKNOWNと初raw観測は保持し、追加時間でGPU/NN/MAXや科学費をresetしない。

310 Dense A/Bを含む4ケースは担当のall-four-reader-stop-v1.jsonへ科学・model・guard読者の停止を保存済み。310の原science01:40/source01:45/save01:50、313の原source01:30/save01:35は変更しない。原Bのmodel開始前admission失敗はNN0/MAX0として保持する。延長自体から第四fit・方法変更・旧個別締切の成功を認めない。313 private NOT_ADOPTEDの後のmain描画移行は、独立315の明示owner/phase/費とsource quietによる別の通常配分で扱う。

記録済み曲線の分析と同条件観測を継続できるが、数百万distinct入力・GPU主経路は観測/代替案/全費の提案までとし、新corpus取得・学習・batch/特徴/教師変更をこの延長だけで開始しない。TT311の有限correctness採用とwhole-caller同NNUE性能/棋力未確認、MPC OFF準備を区別する。終了点検は03:40頃までに通常依頼を受け、運用終了と科学停止/判断品質を別々に記録する。
