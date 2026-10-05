# 実対局1rootの有限horizon・葉由来診断 (254)

この保存rootのdepth1・2では、Dclipの−1は終局敗北ではなく、非終局値のclipによる全合法Action21／29の同値だった。Dtanhと凍結NNUEは両depthで29を選んだ。この有限horizonの順位から実際の悪手、棋力改善、NNUE学習の最高性能は認定しない。

## 固定入力・実装

quoridor-4lc.254 / frame20。249のclip slot4・tanh slot3、ply44・STM1の同board＋全count-history＋prefixを253停止metadataから1rootとして固定した。旧6差分はdepth1〜6の6列であり、6rootではない。今回測定はdepth1・2×NNUE／Dclip／Dtanhの6条件のみ。

履歴SHA `0ec475d57131761ec8c0948a75c9802f5f3354272856e34f7bdc30487ad25d0c`、prefixSHA `9a7cc3629c1b696284e40b007eed573ca987cf8176700253225349a86b00320f`。全合法root Actionsは21と29。元の完成depthの全root順は未記録なので、Action昇順を新診断順として明示した。Dclipのstrict-first 21を元探索のバグや悪手へ置き換えない。

凍結228576BEST2000、12193 f32 /48772B、tensorSHA `b81792d5ba00c6d79b58cada2fc81d84ea822db48c04420b4e269fb9b71841b3`、scaleSHA `68f8b43a0e4408a1546f8fa2652ffdf21f1f7bdcfbac9a25a86ac666b27aa4ee`をreadonly再用。実STM距離の標準化、D係数a=.06038215201109912/b=7.925687690687516、f32順序、terminal優先、fastleaf/fullfallback、history、全合法、TT/noise/policyなしを維持した。新Torch import・fit・モデル更新なし。

各rootchildを剪定なしの全合法列挙でfull-window評価した。極値由来は全有限depthの同値極値をcount/rangeで集約し、由来ごとに1witnessを保存した。個別全leafログ、深い真値、正式holdout評価とは異なる。親copyのkey/history復帰と実child P2/full-deltaを同単job fixtureで確認した。全mutable undo一般保証とはしない。

## 全6条件

値はroot STM。独立のCPU速度比較ではなく固定順の診断費である。

| depth | 評価器 | Action21 | Action29 | argmax | NN | processed | 条件wall ms |
|---|---|---:|---:|---|---:|---:|---:|
| 1 | NNUE | -0.990716636 | -0.983518243 | 29 | 2 | 3 | 0.955144 |
| 1 | Dclip | -1.000000000 | -1.000000000 | 21,29 | 0 | 3 | 0.529335 |
| 1 | Dtanh | -0.928240240 | -0.895173073 | 29 | 0 | 3 | 0.623150 |
| 2 | NNUE | -0.995144188 | -0.989370704 | 29 | 112 | 115 | 29.590813 |
| 2 | Dclip | -1.000000000 | -1.000000000 | 21,29 | 0 | 115 | 15.067237 |
| 2 | Dtanh | -0.938210964 | -0.909522772 | 29 | 0 | 115 | 16.331766 |

Dclipの全root極値はdepth1で非終局clip飽和2leaf、depth2で112leaf。terminalWin／Loss／Draw由来は0。depth1のleaf STM raw uは1.4473773〜1.6455196、clip +1から1回符号反転してroot −1。depth2のleaf STM raw uは−1.7228975〜−1.3266131、clip −1が2回符号反転してroot −1となる。全合法枝の有限極値の同値であり、勝敗の強制証明ではない。

Dtanhの29−21 gapはdepth1 .0330671668／depth2 .0286881924、NNUEは .0071983933／.0057734847。tanhは全非終局uの校正・演算費を変えるため、一般の相対WDL差を飽和解除だけへ帰属しない。depth3〜6の由来はNOT_RUNであり、この2depthの由来を移植しない。

## 全attempt・費・停止

科学MAX1：2026-10-05T02:11:21.020779Z〜02:11:21.255826Z、guardian wall .235053145s、122NN（条件114＋実full/delta fixture8）、357processed（条件354＋合成fixture3）、peak family RSS90,529,792B。CPU2単1／GPU0／Torch0、exit0・全child wait/current exact absent・background cleanup complete。診断entry内wholewallは89.599877ms、背景supervisor command wallは4.675879744sで、異なる境界として加算しない。

背景job `456263da-95fb-4eb4-a1e1-959d7715382d`。submit後Idle→completion元role再開、notification delivered。task `one-root-leaf-254-v1`／schema `one-root-leaf-v1`、実argv・expected output・21 source/input hashesのpre/post束縛PASS。科学停止SHA `1ce86d373b69b72bb3e3d5cdb5cfd6445e3345ec055a735b6b3a7db38d6ef78e`。

preNN管理失敗2件を保持した。最初のnode --checkは閉じ括弧不足でexit1・NN0、修復後に固定した。必要Git保存の最初のHEAD CASは他owner更新との競合でexit128・NN0。作成済み失敗source commit `a384810e30c43d9ffe0b0c6742b042db4e950bd0`を親として保持し、自域subtreeだけfresh HEADへ再構成した。成功科学の再実行・置換なし。

準備管理の過去各command CPUwallは全件個別計測されておらずUNKNOWNを残す。LLM思考・通信・Idle待ちは科学wallではない。新保存工程の実測はpreservation receiptを参照。source/read180s、管理180sの元枠を保持し、未計測費を0に補完しない。

新4MiB予約／3.5MiB guard内に自域source・結果・小archive・必要uniqueGit・temp・最終receipt forecastを計上する。旧予約・未知費の減額、親追加、default index変更なし。保存照合の正本はpreservation-v1.json。原資料へのreadonly SHA参照を使い、PT／dataset／旧rawの複製を増やさない。

## 判断と必要引渡し

clipの等値集合がこのrootの浅い手選択差を説明する有限証拠を得た。NNUEとtanhの29一致は真の最善手・教師rootmeanからminimaxへの妥当性を証明しない。旧249各2W2L、旧236／240／242、229最終NOT_RUN、開封test非選定、173正式非学習は保持する。追加arena、depth、forward、trainingなし。

次最大1案は、既保存8prefixについてRuleA履歴が合法手・終局制約に与える関係を別NN0診断で明確化する方向。現在は未配分・NOT_RUNであり、本scopeでは実行しない。競合するleaf rootmean意味、特徴未入力history、有限horizon、探索費を保持する。

必要証拠は自域input/preregister/settings/result/counter/compact/scientific-stop、guardian admission/actual-start/process、background config/result/notification、およびmanagement-failures。科学前Git `8c98d9a4e131d001902399769c21890544106537`。最終Git/current byte・archive member復元はpreservation-v1.json／Beads notesから参照する。個別有限完了と親最高棋力goal達成は区別する。
