# 282 出力保存だけの修復を一回配分

2026-10-05 frame22 15:26:03/15:31:03/15:34:03/15:36:03不変。既experiment282へ同課題内の一回修復を明示する。旧MAX2消費/qualification296NN/measurement-r1 timeout180.516275秒/UNKNOWNと保守上界/partial65727B・4record回収を保持し上書き/resetしない。一般NNUE/GPU品質の負例にしない。

独立coor source readで search完了→records.push→serde_json::to_writer(File::create(partial),全records) を毎条件実行と確認。直接unbuffered小writeと全record再書込は管理費の有力候補、排他時間実測は未了。4recordだけではphase均衡32rootのK感度を判別できず、位置付き情報/teacher-horizon/独立量への次配分の情報が足りない。同条件を一回だけ出力処理修復する情報価値がある。正式評価/成功補充やK安定性の結論救済でなく、元不成立を残す探索的入口修復。再度不足なら追加第四科学/深さ/seed/K/root変更なしで停止保存。

solewriter範囲は既teacher_budget.rsの出力部分と私有control/config/必要NN0 serializer test、既frame22-teacher-budget自域。BufWriter+明示flush又はto_vec→fs::writeの小変更で、schema/JSON値/順序/float表現を保持。partial/final/prepare/qualify出力の同IO入口は直せるが、モデル/検索/teacher/D計算/入力抽出/K/順序/Limits/precision/generation等は変えない。小fixtureの旧JSONbytesと修復JSONbytes一致・完全decodeをNN0で確認し formatter/check/owned lint、newbinary/sourceSHAを結果前固定。旧source/archive/binarySHA/partialraw/processを保全、新outputはmeasurement-r2別path、旧r1上書き0。

root plan-v1の36planned32登録、late selection4NOT_AVAILABLE、全P1/同family跨phase相関を保持。32×K64/256/1024順循環・96条件を変更しない。必要なら先の回収4recordと新同root/Kの値/Action/π/NN対応を保存解析で確認し、資格CPU/GPUを再forwardしない。高K真値/leaf正解/両side一般/独立seed分散/棋力0。

配分変更は科学MAX3（旧2+修復1）。元総300秒を維持し旧qualification command15.119953+measurement180.516275=195.636228を加算、追加修復hard90秒+回収5秒で総<=300。管理inclusive spanは別で旧失敗184.930911も保持し壁費を0にしない。NNは旧100000をresetせず追加50000の明示一回枠でaggregate150000上界（qual296+旧測定UNKNOWN保守98000+new50000=148296）。source-bound header5376は別observedだが原UNKNOWN chargeを割引してこの配分を作らない。allocated旧12mと原515334観測/UNKNOWNを保持、新上界は新job8m、両stage未確認保守合計20m（親NN/resources変更なし、processed/treeallocated別指標）。旧総NN100k/allocated12mと変更理由を既issueに残す。

同CPU2single/actualRAM2GiB guard1.75/GPU6GiB、新job90秒は1job30分内、actualphysics/loaded/current24/正PIDtick/owner/pause/freshstorageを本人確認。未確認VRAM0扱いなし。旧compile/test120内のremainingを使い再build <=25秒（旧18.44と各既test/lintを保持、実剩不足なら具体不足で科学開始0）。旧sourceprep180/manage90は原保持、新NN0修復prep30秒/manage30秒を明示追加別欄で累積resetしない。新依存/model/環境更新/ゲーム/教師大量取得/学習0。

保持追加2MiBは旧273123MiB確認unusedから移転、273121+2781+282旧4+修復追加2=128MiB総不増。旧scope4MiBの原科学/失敗/archivesを保持し旧forecastを削らない。修復source/data/Git/temp/元結果との必要比較を新2MiB内へ束縛。sharedreleaseは既273128のactualgrowth+新32枠内でfresh確認し不足なら返す、未知128MiB/旧pool保守保持。main/core279の新変更を本人WT/旧条件へ移植0。

最初source/NN0 bytecheckと準備forecastを14:50目安に短報、science/source stop14:57/save15:05（旧14:50/15:00未達/変更理由を保持、親枠延長0）。今個別deadline変更は旧失敗保存と出力管理修復への限定再配分で、4時間起点を取り直さない。新fullreport/RootACK/全役承認は入口条件にしない。本人same task/assigneeで実開始/停止/全waitを報告、予算/保存不成立なら修復NOT_STARTEDにして旧部分結果を有限保存、coor別owner採否と本人自己検証を分離する。
