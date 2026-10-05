# 独立family量と学習仕事の対照 / quoridor-4lc.286

2026-10-05。284は静的解析停止・本人close・backup後に移行。286は本人claim済み、実準備と学習科学を区別する。旧274/280/284の結果・失敗・費・UNKNOWNは変更しない。Git/indexは統括のみ。

## 結果前登録

生成正本は285 v2（新namespace/seed）：最大1248train、固定48selection、96sealed future-evaluation、48family block。v1の1024/64/64は未実行の旧proposalであり、本loaderは受け付けない。学習側は封印future-labelsを開かない。

3 fresh条件は約10k/256000seen、約30k/256000seen、同約30k/512000seen。H32/QF1/routezero4/D保持a0b8、rootmean、Adam1e-4/WD0/λ0、seed19080311、game一様→row一様、旧train-only尺度と初期重みを共通にする。primaryは同seenの終点2000step、仕事対照4000step。曲線点は0/1/5/20/50/100/200/400/1000/2000、仕事対照は2500/3000/4000を追加する。200step/BESTはsecondary。旧B5981は保存値・重みを再用し再学習しない。

統括の287独立レビュー採択により、Vrawは旧固定val1248＋旧選定392＋新selection48のraw入力。Toldは旧学習5981の全seen入力を保守保持する。新trainは全Vrawへstate/historyliteral/実STM-f32入力ORで事前除外し、全saved runで実使用したtrain入力のunionをTseen_finalとして別途束縛する。finalvalは全VrawからTseen_finalのOR露出を除外した一つのmaskであり、largest runと同一だと仮定しない。futureevalはTseen_final＋**全raw Vraw**を参照する。再帰的なmask変更・後からseen行を消した扱いは行わない。全予定行/family・zeroeligible、旧固定/旧選定/新選定の分母を別保存し二重重み付けしない。history形式互換はUNVERIFIED。新48のraw入力が未受領ならsource/scale準備まででfitは開始しない。

最終candidateは新selectionのgroup等重みteacherMSE、tieは少ない仕事の事前規則でNNUE一つをfreezeする。D未達なら採用未支持とし、独立評価を自動省略しない。別ownerが候補+D+旧Bを96予定familyで一度比較する。未来評価後の再選定は行わない。96は十分量の証明ではない。

## 接線・費・不足

WTの現役train/route_trainingを小変更でreuseし、native v3 exporterの式・形式は保持する。学習partitionsをstats/fit前に固定し、actual行数・family数・source/hash・モデル初期・batch順・epochを各run前に束縛する。量が異なるrunの同seedを同batchbitとは呼ばない。大規模2条件の最初2000step batch prefixは一致検査する。

予測は予定evaluation forwardからval全行の小f32値を保存し、finalmask変更の算術再集計を可能にする。全予定stepの重みも保存して一つのcandidateを選べるようにする。追加forwardは全額課金、MAX5/3mNN/3.1mprocessed/1800sを維持する。actualrowsが想定を超えれば結果前に評価点数の明示調整又はtyped停止とする。

285の停止immutable cache/完整prefixと64MiBの保管配分を受領し、16:21に第一段修復r2の学習・parityを完了した。旧r1の管理失敗・源・予約sampleは保持する。後続二条件は第二段のactualデータと別保管採択を待つ。旧openedtest/173は読まない。量不足・過露出・tau分布・教師/leaf・帰納バイアスを競合のまま保ち、教師MSEを棋力へ換算しない。

15:40のblock00 immutable handoff（48train/1527eligible）は受領済み。新selection48のraw refsはまだ未受領。public projectionはstrict whitelistでP2のactualSTM idsを再回転せず、f32 bitsを復元して私有cacheのP1P2→STM入力へ照合する。projectionにtarget/value/winner等の追加fieldがあれば拒否する。

学習parityは24old/new固定witnessのTorch/native full/deltaと、4組のA→B→A accumulator returnを初期/200/終点で確認する。追加288NN/runを事前計上する。後者は固定特徴入力の復帰であり、RuleA盤面のmake-unmake・棋力を認証しない。

## 第一段の実結果（最終mask前）

登録144train familyの4803行はVraw3285へのOR除外0で、旧5981を含め10784train行・276family。state/history-key literal/actualSTM-f32の一致は全0だが、history crossformatはUNVERIFIEDであり全履歴の非露出保証ではない。Vraw=旧1248+旧392+新1645、Told=旧全5981をtarget-free reference-set SHAで先に固定した。

最初r1はcheckpoint親dir未作成でevaluate(0)/trainloop前にexit1。Torch/model初期化は行ったがforward/train0。旧source archive/trace/identity/stopと396978NN・416948processedの保守予約を維持し、MAX5の一entryを消費した。統括の明示prospective修復一回だけをr2として別登録し、親dirのNN0作成・書込検査・衝突拒否を追加した。19小fake、Ruff format/check/lint/ASTを確認した。

r2 actual16:21:10.883157→16:21:18.325456 UTC、CPU1、guardian7.453808s、peak family RSS992292864B、exit0/全wait/currentexact[]。同initial native tensor SHA ec4167、learn256000 +10eval140690 +parity288=396978NN、processed416948。Torch/native full-delta/入力A→B→Aの最大差1.192093e-7を確認。RuleAの盤面undoや棋力を認証したものではない。

固定終点2000のgameequal rootmeanMSEはtrain .053153、旧固定val .353338（D .489404）、新48selection .389866（D .405141）、旧12selection .485642（D .392634）。新48はstep200 .399311、400 .409782、1000 .405472、2000 .389866であり、一様・単調な利益ではない。旧12の悪化は保持する。10曲線・全scheduled checkpoint・val scalar predictionsを保存した。この結果は暫定maskの探索用validationであり、新独立評価・純数量因果・強度支持ではない。最終candidateは後続条件と共通finalmaskの再集計後に選ぶ。

旧B LAST2000（same-seen主対照）とBEST200（secondary）の全3285raw Vraw予測を一つの必要評価entryで保存した。actual16:41:18.479395→16:41:22.251985、3.758832s/peak732016640B、NN6666=2*3285Torch+96native full/delta、processed26636、exit0/wait/currentexact[]。旧weights/PT/native SHAの対応を確認、新train0。累積保守800622NN/860532processed、3/MAX5 entry、残る科学は第二段の一条件ずつ。future labelsは未読。

停止済みdata/exposure-mask/gradient JSONの4425433Bをlossless gzip217000Bへ保存し、byte復元SHAを確認した。curves、prediction order、scalar predictions、全weightsは直接読取を保持し、旧科学数値を変更しない。scope/checkpoints actual約13.2MiB、後続・uniqueGit/tmp込み60MiB見積は64MiB内だが、actualrowsと必要圧縮を次入場で再確認する。Git/indexは統括だけ。


17:16の自然停止点で最終集計の4fakeをNN0/0.137029sで確認した。group/row重み、displacement+alignment恒等式、0eligible分母、重複used-referenceの一致/拒否がPASS、全wait/currentexact[]。旧B予測の登録行順SHAを全runのVraw順と照合する未来版を追加した。formatter/check/lint/14ASTはPASS、科学run源は変更しない。

旧B評価に使ったPython源17memberはarchive32904Bのbyte復元SHAが登録源と一致した。一方、登録時input_SHAへ含まれた未使用aggregate.pyは科学後の集計編集で既に異なり、登録時の全文bytesはcurrentから復元できずUNAVAILABLEである。旧hash/科学preflight記録と二つの管理archive拒否を保持し、復元成功を捏造しない。実baselineのimport/実行依存、weights、予測、科学数値は保存した。coverage訂正は統括へturn/steer accepted、受入れ/独立検証とは分ける。

第二段生成の17:11 producer停止receiptでは、T5–11までで旧込み25517行、T12–15はprep予約不足のNOT_STARTEDである。これはproducerの原停止点であり、約30kの成立又は学習陰性ではない。必要新prefixのimmutable handoff/実数と保管採択後に残2fitを登録する。286はin_progress、futurelabels未開封、旧r1保守予約/MAX1は維持する。

第二段最終（2026-10-05 17:51 UTC）：144→576新train family、旧132込み708family/25517行で実施した。30000行はNOT_REACHED。256kseenは17:50:17.229244–17:50:31.429135、544308 NN/14.180072秒/peak1166557184B。512kseenは17:50:59.444671–17:51:15.309214、886714 NN/15.852354秒/peak1171529728B。両entry exit0・全wait/currentexact残0。初期SHA、同25517入力SHA、first2000 batch prefixが一致した。失敗entryを含めMAX5/保守2231644NN・2360960processedを使用し、追加fitはしない。NN0入力準備69406metadata行は科学processedとは別に記録する。

固定Vraw3285全行の最終OR除外0、84group全適格。同最終maskの新48family gameequal rootmean MSEはstage1-256k LAST .389866、stage2-256k LAST .227772、stage2-512k LAST .264937、D .405141。同seen増量では選定誤差が減ったが、分布・epoch・旧データ再用の交絡があり純数量因果ではない。仕事増加はこの終点で利益を示さなかった。旧固定24groupは .353338→.267716→.270631、旧selection12groupは .485642→.280774→.400778。全予定曲線と群別分母は finalmask-selection-v1/all-finalmask-curves.json。

登録済み最小新selection gameMSE・同値時少ない仕事規則でstage2-256k step2000を候補freeze。candidate-external-freeze-v1.jsonはcheckpoint/native weights/manifest/全source停止・共通mask・Tseen_finalとALLrawVraw参照をSHAで束縛する。未来96labels未読、独立287が一度評価し、結果を再選定に戻さない。history crossformat UNVERIFIED、native確認は固定入力full/delta/入力親buffer復帰であり、完全RuleA undoや棋力認定ではない。

公開zへの移行前にlearning-source-before-public-z-v1.tar.xzを32,644Bで保存し全member byte復元確認。旧baselineで未実行aggregate.pyの歴史bytes不足は従来proofのまま保持し、科学依存源と原成功を置換しない。大きい準備JSON/停止後診断JSONはlossless gzip/原SHA/byte復元proofで小保存し、入力・予測・重みを削除しない。現在Python源の停止path/SHAと全attempt費はfinal-science-source-stop-v1.json。Git/index操作は統括のみ。
