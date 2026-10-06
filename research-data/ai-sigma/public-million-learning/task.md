# 公開Sigma 100万行・GPU学習の実行依頼

Beads `quoridor-4lc.319`。ユーザーは2026-10-06、Rootの100万行GPU学習案を承認し、待機中の学習セッションへの実配分を指示した。旧待機限定契約をこの仕事に置き換える。固定チーム、過去frame、旧GPU残予算は再開しない。

## 目的と選択済み方針

公開Sigma全43 NPZの全域から訓練1,000,000行、validation 50,000行、最終評価50,000行を構成し、現QF1＋距離logit残差H32のGPU学習を実施する。これは保存する適格観測行数であり、distinct盤面数・独立game数・学習seen数ではない。学習効果、過学習の推移、GPU供給から保存までの全工程を確認する。小候補の距離超えや全43 distinct数の確定は開始条件にしない。

- 固定公開source `751186344fc52ad0c29bc65922e62c6fa915f006`、43 NPZ（18,914,078保存行、compressed合計1,664,424,671B）を既存source manifestで確認する。ネットワーク取得とboundedなdecode・変換を今回許可する。同blobを必要範囲で再用し、単一shardずつ処理して全rawを保存しない。
- 全43ファイルに機会のある固定seedの抽出・分割を行う。先頭行、先頭入力群、直近数cycleだけを採る方式を使わない。source/shard/row index、採択確率・件数、原入力とモデル入力の資格・SHA、各分割の実distinct数、phase proxyを記録する。全体の完全な重複除去・全域入力ledgerの完成を恒久gateにしない。
- 入力・座標・範囲・finite・合法到達性など、証明できる不正を除く。公開z0は不正と断定せず、終了理由が不明な教師として初回学習・選定・最終評価から除外し、元値と除外理由・分母を残す。有効な同入力の複数勝敗観測は保持する。1群の不正から有効な別観測を一律に消さない。
- 訓練とvalidationの盤面一致を理由に訓練行を削除しない。同じ元観測のコピーとoriginal/reflectionの兄弟は同じ分割へ束縛する。反射対応はsourceと実byte/非対称壁fixtureで確認し、見かけの入力一致から由来を捏造しない。異なるcycleの同盤面は許容し、source game/history欠測を独立gameの証明にしない。
- 分割・抽出seedと規則は結果前に固定する。最終評価labelsはcandidate/config/checkpoint選定規則freezeまで別出力でsealed。過去の開封済み43/RuleA48/96/173を新しい未見評価として扱わない。可能な元観測IDを旧使用manifestと照合して露出を報告し、確認できない履歴はUNKNOWN。新testは公開分布のheld-out観測評価であり、完全な未見game棋力評価ではない。
- 主samplingはepoch shuffle、各epochで全train行を一度ずつ消費し、最後の小batchも記録する。主loss/validationはrow平均、入力群等重みと既知/未見入力・source/phase別はsecondary。入力群を均等抽出するgame samplerを公開inputgroupへ代用しない。尺度・距離/定数基準はtrainだけで固定する。

## 実装と学習

既存の現役 `python/quoridor_training` とRust `quoridor-data`/runnerを拡張し、省容量cacheとbounded batch供給を実callerへ接続する。100万行dense tensorの約2.51GBを新保存768MiBへ押し込まない。bitset等のlossless表現から必要batchだけ展開し、元入力・モデル入力・ラベルの対応をfixtureとnative資格で確認する。全行JSONの巨大metadataや全row Python dictを常駐させない。新しい学習器コピーや互換shimを残さない。

モデル/特徴/targetはQF1＋D残差H32/route4 off/decisive outcome zを維持する。新特徴・幅・方策・teacher生成は行わない。初回はAdam、weight decay 0、FP32、LR3e-5、batch128のepoch方式を基本にする。低LRは旧詳細曲線Bの末期退行の小ささを開始根拠とし、新corpusで最適と認定しない。

GPU供給の実装資格としてbatch128/512/2048の短い計算・転送計測を合計30秒以内で行える。学習重みを選ぶ実験に使わず、同固定入力・初期重み・数学で時間/VRAM/数値を確認する。128から変える場合は、数値対応と全費の結果に基づく推奨batchと理由をRootへ渡し、Root経由の人間判断前に本fitのbatch/LRを変更しない。128でもGPU本fitを開始でき、大batchの判断待ちを全作業gateにしない。

初回one fitは最大20epochs、validation primary rowMSEによるearly stopping（patience3epochs/min_delta1e-4）、GPU全job費3600秒で止める。短い資格失敗の通常修復は可能だが、LR・モデル・データ・教師のsweepや本fitの自動再学習は行わない。1,000,000seenは1epoch相当であり、100万種類でも完了学習でもない。予算内で途中停止ならactual epoch/step/seen・coverageをそのまま報告する。

曲線はstep0/1/2/5/10/20、最初2000更新は25更新ごと、その後1250更新ごと＋epoch境界を初期案にし、最大250点に結果前に束縛する。固定train診断subsetと全validationを同forwardの保存値から集計し、eval費を課金する。epoch境界にはtrain全件誤差も測る。evalが支配する場合は、dense初期観測を残し、結果を見て勝手に間引かず全費と予定点をRootへ報告する。

CSV/JSONにstep、seen、actual completed epochと進行率、wall、train診断/fulltrainの区別、validation row/group MSE、距離/定数基準、符号・飽和を保存し、PNG/SVGを出力して画像を確認する。補間を実観測にしない。initial/BEST/LASTと凍結候補、native full/delta/undo/STM/ScalarSIMDの対応を限定確認する。訓練・選定の完了後、一候補/D/定数をsealed最終評価へ一巡する。評価後の再選定・訓練転用・新arenaは未配分。

## writer・資源・停止

- 同じsaved thread `01a1100f-6d45-78e0-8a87-84503ff0fbf6` を再用する。Root同fullaccess（danger-full-access/never）、同model/effort。cwdは新managed WT `/workspaces/quoridor/.worktree/learning-million`、base main `d61a91d`。本人はready/show/ownerと実cwdを確認してclaimし、待機解除を実開始と区別する。
- 本人一人がWTの `crates/quoridor-data`、runnerのdataset/cache入口、`python/quoridor_training`、対応tests/config/docsを編集する。core/ai/nnueの探索数学・モデルレイアウトは変更しない。Rootのみmain/Git index/commit統合担当。stage/commit/ref/merge操作・main source書込・再帰委譲は行わない。停止path/SHAでRootへ引き渡す。
- CPU最大2logical（探索318の0,1を避け2,3を候補にactual affinity/topology確認）、RAM family最大4GiB、VRAM最大6GiB。検索profile測定とCPU/GPU計時・共有Cargo target buildは非重複にする。前のjobを無断interruptしない。限定private target増分は本予算へ。
- 初回実data取得/decode/変換/資格は累計7200秒、compile/testsは600秒、GPUfit/qualification/transfer/eval/init/failure/recovery合計3600秒、最終CPU/native評価・解析300秒。取得最大固定43blob compressed合計に再試行30%まで、全attempt費を記録。旧GPU7200 UNKNOWN/旧3600残3586秒は保持し、本新配分と混同しない。
- 新保存768MiB inclusive（compact corpus/index/provenance 512、shard scratch96、build/source/WT48、weights32、必要evidence/Git/temp80MiBが目安）。Rootのfresh directed admissionと再配分を参照し、旧保持12GiB/UNKNOWN128MiBを維持する。Rootは終了済み273/274/275 future growth512MiB、旧1d2 growth160MiB、完了maintenance future growth96MiBを前向き移譲する。旧current資産・科学費・失敗・原capは変更/削除せず、未使用future予約の使途だけ変更。新rootをaggregateへ追加してpeak含むforecastが成立するまで大取得/computeは開始しない。自己tmpの不要scratchはSHA/provenanceと資格後に撤去でき、共有cache・旧資産は削除しない。
- 通常の実装詳細・修復・lossless転送は自律的に進める。100万行の意味変更、未知0の教師採用、重要なsplit変更、batch/学習/特徴変更や容量・時間超過が必要なら具体不足・競合・全費をRootへ戻す。達成不能なら不足件数を報告し、繰返しで100万行へ水増ししない。
- 長jobは既存research-jobのguardian/子回収/一度の完了通知で起動してturnを終了する。周期的LLM監視・固定role・新server/cronを作らない。pause、owner変更、budget超過、入出力不整合、未解決の重大資格不足で自己子を正確に回収し停止する。

## 成果と受入れ

初報はclaim/actual cwd/固定source/資源admission/実取得・実学習の開始有無を短く報告する。次はデータ実分母・distinct/alias・GPU供給の意味ある結果、学習曲線、最終評価、重要判断か障害の節目でRootへ通知する。Root thread `01a0f2e9-357d-7ef3-a2fe-b16f80accda5`、宛先issue `quoridor-4lc`。定型通知のためのturnを作らない。

新split/入力変換/教師解釈はRootが導入境界を別担当の独立レビューに回す。該当採用・最終評価releaseはレビュー対象、毎run全員承認ではない。実装・準備・測定を全稿待ちで止めず、必要境界が未確認ならその採用だけ保留する。

停止時にsource/process/正確child回収、変更path/SHA、取得source/hash/配布条件、実分母/除外、元観測aliasとsplit、cache/input/model binding、曲線/画像、whole費、checkpoint/freeze/評価と限界、未完了と次判断を残す。raw/model/cacheはignored assetsへ、small manifestと必要圧縮証拠をmain専用保存先へRootが統合する。Beads status/backupを本人が維持し、最高棋力・独立game汎化・新データ量だけの因果を先取りしない。
