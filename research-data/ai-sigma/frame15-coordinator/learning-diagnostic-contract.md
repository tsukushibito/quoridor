# frame15 学習診断: 最適化・早期汎化と競合説明の少数対照

担当hypothesis saved01a0f31c-2e4b-7170-82c5-69e1428c2418、worktree /workspaces/quoridor/.worktree/ai-sigma。新frame15許可03:51:38–05:51:38UTC。goal/本人issue ready/show/no pause/担当確認→claim/static実開始を記録。204-finite-acceptanceに基づき旧204本人close+backupをこの実質taskturnで先に行う。旧204科学/期限/成績は変更0。現common/role207を適用、root再確認待ち0。

## 問いと選定前の見解
原全層QF1はtrainをfitする一方、val評価0→100stepの間が未観測で、最初100stepは96trainで2.75epoch（24train10.52epoch）。Adam.001だけ中心に進めL2/headfreezeを優先した前判断を訂正する。競合説明は(A)LR/初期更新量/早期過学習、(B)活性/勾配/出力制約又は入力尺度で情報を利用できない、(C)教師ノイズ/history不足/分布差。これらを一つに断定せず標準診断・既知の方法と比較する。
最初10分以内に現在の不足・有力代替・結果で変わる判断を返す。初期選定案は原plain QF1-H32・同96train4653/val1248・同mask10b502cd/初期seed19080311・rootmean/gameequal・AdamWD0/batch128を維持したLR1e-3/1e-4/1e-5の短対照。初期0/1/2/5/10/20/50/100/200/400step等でtrain/val・epoch・seen samplesを記録し、最初数epochの改善を見落とさない。固定400step自体は必須でなく、総予算内で有力3–4条件と必要な小sanityを自主選定、結果前に問い/条件/変更理由/比較範囲を登録する。criticの選定前見解を必要範囲で使い、単なる全役承認待ちにしない。
既情報距離基準は固定参照。旧96-r1曲線とbaseline/constantは再用し、原記録は書換えず新観測を別runへ。頭だけ学習/clip変更/新幅/追加teacher/arenaを当初主仕事にしない。必要な小標本fit又は有限差分は今回の問いへ寄与すると判断した範囲で同課題・総予算内、固定tinysubsetをlossを見る前に選ぶ。既fulltrain低誤差は学習機能の根拠だが正しいview/一般化/勾配全範囲の証明ではない。
層別観測はft/h/outのgradient norm/zero割合、活性分布/dead率、weight norm/実update-to-weight比、出力とtarget/飽和、距離と疎入力の尺度を固定少数train witness又は同minibatchから集約保存する。observerの追加forward/backwardは明示課金し、巨大per-neuronログ/全copyは不要。モデルtrain/eval切替・optimizer対象・初期SHA/同batch order/監視負荷の交絡を確認する。NaN以外に有限だが0gradientも見える観測を用意する。torch組込層へ無差別に全数gradcheckを必須にしない。

## 単writer/データ
自域 tools/ai-sigma-learning-diagnostic/、research-data/ai-sigma/frame15-learning-diagnostic/、models/experiments/nnue/frame15-learning-diagnostic-*/、docs/reports/ai-sigma-hypothesis-learning-diagnostic.md。旧tools/nnue-training/・モデル・194/195/197/200/204 source/旧runはreadonly、thin reuse/instrumentだけ。主手順書を変える必要があれば停止と所有移譲を統括へ返す。oldtest labels/results/teacher/journal/mixedstatus/previewは読取0、173正式198非学習。許可データは194 final-QF1 train96+valの5901行/既stage96/maskと停止source、testmetadataもこの診断には不要。
validationは再用する探索的選定用、未見独立評価とは呼ばない。少数LRで改善しても原因唯一/最終NNUE性能/棋力は認定0。次節目で新独立testが必要かを残時間/利益/費用で統括へ提案し、小調整ごと一式を自動要求しない。

## 費用・停止
CPU2単1/torch1、RAM2GiB currentguard1.75。学習/評価各jobhard120s・全heavy600s・全science samples800000（train/eval/追加forward/gradcheck全課金）、warm0/GPU0、新teacher/game/build0。最大4条件、同課題内の必要software修復/反復は総額内で版/全attempt保持、結果救済に既test/原期限を変更しない。heavyは現CPU0短NN0criticと測定重複を避け、scheduler/monitor・他科学process/PIDtick/RSS/ownerを本人直前admit。自然supervisor CPU0は継続し窓/current確認、source静的準備を92全史確認待ちにしない。
保存はhyp既64MiB内の197予約16MiBから確認済未使用8MiBを本scopeへ振替する案。旧197必要current+uniqueGit+残metadataが8MiB以内か本人確認して旧197retain8/newscope8、親総量追加0/旧unknown減額0/必要結果削除0。確認できなければ静的準備の小保存を先行し統括へ具体不足返す。新scope guard6MiB、source/compactmetrics/curves/少数weights/archive+uniqueGit/tmp/remainingmetadataforecast5MiB、全旧sharedhyp guard56MiBと予約64内を直前確認。ログ肥大前に集約・必要保存、guard超過で通常write停止。
新診断science開始04:45まで、科学停止04:55、process05:05、提出05:15（受領+75分の早側も適用）。この段は最初の判別であり親を全消費せず、5–10分内の小成果/実費/次判断を返す。必要source/input/hash/config/再現command/全条件/curve/原因に対応した観測/typedfailure/stop/所有子wait/currentexact不在/localGit/必要bytes復元/defaultindex不変更/Beadsbackupを保存。受付/claim/static/actualNN/成功/採用は別追報。未完でも射程保存・close可、goalclose0。
