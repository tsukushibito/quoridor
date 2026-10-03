# 現在の優先順位と教師生成・学習計画

2026-10-03 frame12。許可08:47:38–12:47:38UTC、heavy12:37:38、監督12:42:38、monitor12:45:38。親期限・運用は92/steward単独所有。native主検証と教師生成の効率化、独立lineageから全手π/rootNN/rootmean/z→game split→自前学習・評価が主経路。NNUE最高棋力は最終目標、Sigma同等は未認定。旧173正式198局95勝103敗・逐次閾値未達の不確かという結論/失敗/期限を保持し、学習へ転用しない。

## 現在の問い・実配分

| 優先 | 到達点・担当 | 費用・次の判断 |
| --- | --- | --- |
| 完了180 K800 | 3固定入力の候補現wrapperはJS参照より中央値23〜33%長い | root800edge799/全30/NN24000。initial C/R1.322332、asym1.325008、jump1.229342、bridge2404往復/約8MB。有限速度の比/幅だけを回答、速度等価margin未設定・C++未実測 |
| 主181 experiment | 最終checkpointだけに薄修正→sameK800 old/new/JS→教師生成実費→24新独立lineage→既CPUlearner継続 | 総heavy1800s/NN240000、CPU最大3/RAM4guard3.5/新256MiBは既2044内。新版採否/teacher engine選択を結果前固定、GPUcurrent不採用継続、原173教師0。science12:25/処理12:35/提出12:42 |
| 182 critic独立検算 | 180全30保存算術/費用範囲と181の取りこぼし・選定を評価 | NN0/static120s/CPU0/新2MiB既guard内。181開始gate0。比から純言語/棋力・全分布へ広げない |


180は新現在配分であり176個別期限を延長しない。176の必要最小pack/Git復元/backup・旧writer/科学子停止を終えて新自域だけ開始。旧GPUbranchの盲目再試行はしない。C++公開学習経路、browser棋力、正式NIは本測定と別の未実測/未達として残す。計測が教師量/学習へどう寄与するかで次配分を決め、速度診断を自動連鎖しない。

## 確認できた基準と採否

176CPU自己対局24GOALからRpolicy/Rz/Rjoint各1409、K64/root64edge63、train20game1188/validation4game221。179は全1409行のπ合法mass・独自P2jump/wall/z/side/split/4重複算術と共有RuleA全24教師1409手＋新4診断110手再生を有限支持。必要12Gitblob、dataset/checkpoint/ONNX実SHA、source/子停止、backupへ統括bindingし179を引継close（受入れcd4ce173）。共有RuleA/保存reload-forward receiptの限界、全deep/state独立holdout保証0を残す。crossgame16key37occurrence、train-validation共有0。

成功production198.496598s=7.098358適格行/s。記録compute全attempt235.726026s＋export/overlap既知小計236.583166s≈5.956行/sは研究費を含む別分母。入力生成/開発/一部admissionwall/管理費はunknown。Rpolicy/Rz/Rjointと未知/全attempt費を別記し、成功速度を総研究率へ置換しない。

CPU200step/checkpoint/ONNX接続を有限支持。保存validation πCE3.903287→2.514467、zMSE1.047608→.684094、train zMSE.207420。未学習初期基準とのfit改善と新診断0勝4敗を区別する。教師不良/hidden32の能力/200step不足/分布不足のどれかを現在証拠から一意に選ばず、同接続診断の反復を学習成果の代用にしない。

177GPUbatch有限数値/route費受入れ後、176で実生成を比較した。原firstCPUrootのVM checker/raw欠測はUNKNOWN・旧条件の6slotはNOT_STARTEDのまま。新NN0teacher001保存first/finalroot joinは原missingtape救済ではなく、新有限根比較として採用。CPUargmax13とtau1実行89を分離、rootNNtol/piL1=0/訪問一致、deep未確認。新futureCPU3→CUDA3は全6GOAL、両backend各188適格行・NN10594、保存採用188根の経路/訪問有限対応。CPU21.251523s=8.846425行/s、CUDA54.711141s=3.436229行/s、比.388431。current3arena/maxB2/.25ms/FIFO経路は生成利益なしとして不採用・CPU維持。GPU一般の無効を主張せず、177B2単route2.72倍を生成倍率へ転用しない。元CPU24学習への新比較siblings混合0。

監督ff1307b0/b811d33aの提案を採用：教師効率と学習価値を別裁定し、既保存π/z別損失と未学習基準を先に見る。次主教師案はlineage/局面多様性を増やし未知lineageへの効果で選ぶ。追加baselineforward/全役承認/新監督層を入口にしない。GPU比較の採否・K800の実支配費・次主データ生成と学習結果を後続節目で確認する。

## 資源・運用

CPU4logical合計/RAM8GiB/保持と有効未使用予約12GiBを維持、NN重jobは競合させない。experiment2044MiB、hypothesis20MiB/guard19MiB（旧173の確認済unused4MiBだけ移転）、critic112MiBguard。旧保持削除/unknown減額/親増額0。180新32MiBはexperiment内、CPU2単1solo測定、管理/providerも同core。GPU学習の累積2h未使用残は不明のため現在配分0。環境/モデル/effort/AppServer/main統合/push/公開変更0。

92frame12は08:58:38freshstart、scheduler3352074/start27085893・monitor3352088/start27085920、親SHA0e0e03a157e86bb9d9b7bd0659fb17a3c413afac2286944a5fde839336baae50/24hash一致を本人報告。自然監督のobserve/早期notes/backupと後のturn_limit/interruptedは別、全期間・外部NN停止保証0。監督10:19:23finish有限成功を受領、未来12時台の停止責任は同92。運用sourceはcoordinator編集0。

176最終8543b550の必要12Gitblob/current、archive e559c173/439member/必要3member byte復元、owner writer/科学子停止・backupexit0を有限確認し統括受入れ。旧source-stopと新GPU停止は別、benchmarkはCPU本学習へ混合0。179の独立CPU裁定と合わせ176は統括引継close、180新scopeを既experimentへ10:32:50 actual steer配送、rootへ10:34:03実依頼報告済み。本人claim10:36/科学開始10:39:12→終了10:42:28、全30完成を受領しrootへ10:48:26実結果を配送。180保存の必要12Gitblob/68archive member概要・必要3member/hash・median/statusを統括有限照合して受入れ、次181へ実配分する。監督53f0f8eaの結果後marginを設けず比/幅を示す案を採用し、181以降の費用規則と旧180判断を区別する。

監督c42df5ceの評価改善を採用。181の追加200step/旧新train混合の前後損失は、この継続学習条件で未知gameへのfitが変わった有限結果として扱う。多様性だけの因果効果は追加学習量・旧データ再露出と分離していないため未確定。原val悪化とπ/z間の交換も残し、対照追加runや新gateを義務化しない。担当experiment、効果確認は181学習報告。
