#216 phase4 — raw residualridgeのtrain-game CV少数λ診断/実配分

phase3 raw626 train .16137/val .78145の大きいfit-transfer gapを受け主計画を更新。最大未解決はこの高次元加法的補正が低正則化の分散に負けているか。frozen standard200hidden age案は有力保留、低NN費用だがfeature年齢とreadoutを変える前に、現在のraw probeの直接的な汎化制御をtrain-group CVで安く問う。raw特徴は教師で学習したencoderではないのでfoldラベル漏れを避けたwhole pipeline CVが可能。fresh test/新teacher/幅/LR全sweepを先行しない。

Same216 solewriter/元scope、別raw-cv-control新source/config/result、phase1/2/3原source/results/Git/stop不変更。NN total29505/30000 unchanged/newNNモデルforwardoptimizerGPUteachergame/test0。実STM raw626/distance2/同rootmean/4653train96固定、元24validation1248はfold/λfitへ不使用。

結果前固定: 5gamefold、6cohort each16gameをUIDのSHA(seed frame16-216-CV-v1)順に並べi%5へ割当、family/gamegroup跨fold0、予定foldgroup24/18/18/18/18を保存。lambda候補 .01/1/100 の3点だけ、単一game-CV診断内で扱う(巨大sweep0)。各foldのtrain-only gameequalpopulationmu/std/zero列、baseline distance WLS a+b*sもfoldtrainだけからfit(既globalDをfoldheld labelで決めない)。eD_fold=y-clamp(foldD)にraw residualridge/intercept非penaltyをfit、heldgame rootmean誤差を全96各game平均へ戻し、lambda選定はOOF gameequalMSE最小・1e-10同値なら大λという固定規則。foldCVは特定教師分布/固定game割当の診断、最終testとしない。OOF row/game/phase/cohort/coverage/zero-variance-unseen列を保存し、foldbaselineDと比較、単純fold平均でgame数差を無視しない。

選定lambdaを全train96へ一度fit。fulltrainbaselinea,bは既199trainWLS/f32Dと有限parityして同Dを再現し、異なる場合typed差を保存。fulltrainmu/stdと原rawsource規約保持、predictionf32/clamp。全trainと固定24valで同D・既raw.01・distance2・learnedhiddenridge・standard400に同weight/rootmean/z/sign/残差decompositionを比較する。validation利益でλを選び直さない。selectedλが端点なら探索範囲内のみの判断をし、追加値自動0。value/rootmean vs棋力を分け、再用valなのでOOF/valを独立testにしない。

予算: 残staticは実最新130.949103/180を保持、追加sourcepreflight上界5s+allCVfitattempts40s<=残49.05内、eachjobhard35s(管理plot/Git費別)。CPU2/BLAS1 NN0単1/RAM512guard448、行列RAMのみ/何個も全X保存0/新環境依存0。もし現残量またはparent/currentphysics不足なら具体数値で停止し、静的計画/Git保存は進める。既16MiB/14guard内の直前actual+Git/temp残forecastに新CV compact500KiB以内、NNcap/親資源増0・oldunknown discount0。curve旧pred圧縮archiveの既所有復元可能重複整理は参照/所有確認した自域のみ、未知削除0。

current owner/no pause/PIDtick/RAM/92正monitorowned/quiet/CPU0critic科研を直前admit。firstmath07:10/stop07:15/report07:20/保存07:30、親07:55:50内。219 criticを新科学問に別120s/1MiB(old217180reset0)で事前/最終必要算術へ実配分予定、全稿承認gate0。旧217/218は停止保存有限受入れ後closed、重複role起動0。

結果で変える判断: OOFが強い縮小を支持してfullval改善するならregularization/data effectivegame数を主な有力説明として次学習方針を選ぶ(唯一原因0)。OOFは改善するがval改善しなければ分布/coverage/teacher/history・CV varianceを保持し追加λ反復を止める。どのλでもD未達なら単純raw加法的候補の利益不支持、保留standard200representation age 又は既知targetの学習sanityを次に比較する。どの場合もfresh testを自動生成0。
