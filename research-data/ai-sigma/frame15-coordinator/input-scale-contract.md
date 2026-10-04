# frame15 距離入力の条件付け：初期関数を保存した標準化1対照

担当 experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746、worktree /workspaces/quoridor/.worktree/ai-sigma。frame15現在許可05:51:38終了/親CPU4 RAM8 保存12GiB不変。ready/show goal+self/no pause/担当→claim。旧205はframe15-coordinator/205-old-preservation-finite-acceptance.json根拠で本人close+backupをこの実質taskturnで行い、旧科学/期限/結果不変更。モデルeffort/既saved/依存環境不変更。

## 問い・選定理由と競合
209は原全層QF1のLR1e-4/step200でval初期改善を2jointseedで再現したが、距離基準.485147に及ばない。元seedBEST200val.6598473195、400.7196768814。初期grad非0/飽和非主因、同固定12train witnessのsynthetic距離局所方向感度はinitial/BEST/LASTで非0に成長（局所合成観測だけ）。B距離入力利用/optimizerのcoordinate conditioningを標準的入力標準化1対照で判別する。低LR・早期停止候補は維持、教師/履歴/分布・容量Cは残す。低LRの延長/幅変更/headfreeze/新teacher/test/arenaより、既情報を使う更新の費用が小さい本対照を選ぶ。感度が小さいこと自体を唯一原因にしない。

## 結果前固定
原plain全層QF1-H32、原96train4653/val1248/max96mask10b502cd、seed19080311、同batch order、AdamLR1e-4/WD0/batch128/rootmean/gameequal/400step、points0,1,2,5,10,20,50,100,200,400を保持。唯一新条件はtrainのみから2distance列のgame等重み平均mu/標準偏差sigmaを求め、実STM f32距離を (d-mu)/sigma にする。2mean/varと算式、0variance処理を結果前保存（sigma0ならscale1等typed処理、旧split/target変更0）。同情報・同モデル容量、無labelのtrain入力だけで計算、val/test統計でfitしない。STM並び・P2処理・疎特徴は原canonicalをreuse。sharedsourceを書換えず私有wrapperにする。
原初期seed tensorを再用しhidden距離2列W_d/biasに W'_d=W_d*diag(sigma), b'=b+W_d*mu と変換する。private.forwardに標準化を置き、原raw distance初期関数を保存する（mu/sigmaはf32で保存し実使用）。初期関数一致を原initialと全5901train/val行で1回照合、maxabs<=1e-6を事前finite基準。これは追加5901forwardと課金しtrain/val内、原weights/test再選別ではない。新initialtensorSHAは変わるので同tensorではなく同初期関数parityと明記。有限不成立なら学習開始しない、まず原因保存・必要な薄修復は同課題予算内、成功runの救済置換0。
全trainable ft/h/outを維持、dropout/scheduler/target/出力tanh/幅/clipを変更0。moments/optimizer初期0、同raw input rowID/batch SHAを原209と対応。初期関数以後のoptimizer座標と実効update差がこの介入、情報を増やした又は学習率だけの効果と主張しない。
primary結果は200step valgameMSE minus 原209LR1e-4の200step .659847319505419。同seed・同samples・同batchの更新対照、新10点curveを残す。初期/定数.6787804677/距離.4851468131との差、train fit到達量/epoch/samples/wall、val24game/phase/z/sign/saturationを併記。best点は探索secondaryで、結果を見て新点/LR/seed/幅を追加しない。validation再用/単seed、一般化/棋力/NNUE最高性能は未認定。
層update/activeFT/同12固定train witnessの予測0比/入力尺度/活性を原209停止observerの薄reuseで記録できるが全詳細装備を新gateにしない。実function spaceとparameter座標の変更を分ける。旧400step再学習対照0、旧baseline原curveとparity参照をreuse。

## 所有・データ
唯一writer tools/ai-sigma-input-scale-control/、research-data/ai-sigma/frame15-input-scale-control/、models/experiments/nnue/frame15-input-scale-control-*/、docs/reports/ai-sigma-experiment-input-scale-control.md。tools/nnue-training/と209 source/outputs/モデル、親/role/common/92/mainmirrorはreadonly。同hyp209scienceは04:36:34probeまで全wait stopped; readonly hashを結果前bind、旧run Git全稿待ちはgate0。model.pyのraw Modelとstopped observerだけ必要範囲reuse、依存取得/共有環境更新0。
既all144 label-free containerはloaderが読むがtest行をlabeljoin/model/moments/witness前に除外し、この事実を保存。train-vallabel5901のみ。old standalone testlabels/results/raw/journal/mixedstatus/previewは未読、173正式198は非学習。未見test自動生成/評価0、候補昇格0。事後追加対照は新判断待ちだが通常修復にはroot承認要求0。

## 費用・期限・完了
CPU2単1/torch1/RAM2GiB guard1.75/1jobhard120s、science allheavy180s/全NN等価sample200000（予定110210train+eval +5901初期raw parity=116111、実additionalは全課金）、warm0/GPU0、新teacher/game/build0。CPU0 critic短算術と重複せず本人freshcurrent/pause/PIDtick/RSS/自然supervisorowned次窓を直前admit。自然supervisor CPU0は継続・period変更/interrupt0。
新8MiBをexp既1980MiB poolの確認済未使用から自域予約、guard6MiB/current+uniqueGit+temp+finalmetadata forecast5MiB。旧194/201/203/205の必要保持/unknownを減額0、親保存総枠増額0。本人旧pool/current/unusedを直前確認、未確認なら静的sourceを先行し具体不足返す。必要入力・curves・weights小archive/source/hash/config/全attempt/必要bytes復元/Git/defaultindex unchanged/Beadsbackupを保存。
newscience05:05UTC、sciencestop05:15、process05:25、submit05:30（受領+55分の早側）。5–10分内選定前見解・薄実装/数量不足を短報告、原input関数parity→actual1run→primary/全24val/費/停止を返す。support/negative/inconclusiveいずれで完了可、原因唯一/棋力認定0。次最大1方向を具体化。科学終了後必要保存とhandoff、個別close・goal達成を区別。