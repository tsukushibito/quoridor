# 現在の優先順位と教師生成・学習計画

2026-10-03 frame12。許可08:47:38–12:47:38UTC、heavy12:37:38、監督12:42:38、monitor12:45:38。親期限・運用は92/steward単独所有。native主検証と教師生成の効率化、独立lineageから全手π/rootNN/rootmean/z→game split→自前学習・評価が主経路。NNUE最高棋力は最終目標、Sigma同等は未認定。旧173正式198局95勝103敗・逐次閾値未達の不確かという結論/失敗/期限を保持し、学習へ転用しない。

## 現在の問い・実配分

| 優先 | 到達点・担当 | 費用・次の判断 |
| --- | --- | --- |
| 完了180 K800 | 3固定入力の候補現wrapperはJS参照より中央値23〜33%長い | root800edge799/全30/NN24000。initial C/R1.322332、asym1.325008、jump1.229342、bridge2404往復/約8MB。有限速度の比/幅だけを回答、速度等価margin未設定・C++未実測 |
| 主181 experiment | 最終checkpointだけに薄修正→sameK800 old/new/JS→教師生成実費→24新独立lineage→既CPUlearner継続 | 総heavy1800s/NN240000、CPU最大3/RAM4guard3.5/新256MiBは既2044内。新版採否/teacher engine選択を結果前固定、GPUcurrent不採用継続、原173教師0。science12:25/処理12:35/提出12:42 |
| 完了182 critic独立検算 | 180全30保存算術/費用範囲と181の取りこぼし・選定を評価 | NN0/static120s/CPU0/新2MiB既guard内。181開始gate0。比から純言語/棋力・全分布へ広げない |


180は新現在配分であり176個別期限を延長しない。176の必要最小pack/Git復元/backup・旧writer/科学子停止を終えて新自域だけ開始。旧GPUbranchの盲目再試行はしない。C++公開学習経路、browser棋力、正式NIは本測定と別の未実測/未達として残す。計測が教師量/学習へどう寄与するかで次配分を決め、速度診断を自動連鎖しない。

## Sigma型の多数game多重化とGPU共有batch

root経由のユーザー質問に対し、これまでの具体配分にこの経路の実生成検証は含まれていなかったと明記する。176の3arena/maxB2不採用は当該実装だけで、少数CPU workerが多数の独立gameを進め、共通GPU queueでより大きなbatchを集める方式を除外しない。

固定[自対局source751186](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/selfplay_cpp.py)を確認した。CPU threadsとparallel_gamesは別引数で、既定はthreads7/parallel2048/leaf-batch1/max-batch1024、中央get_batch→GPU→put_results。これらは設定値であり実効batch・旧checkpointの歴史設定の証明ではない。sourceは共有NN cache、leaf parallel/virtual loss、noise/FPU/temperature、PCR/solverも持つため、この生成構造の再現と、固定Sigma C++の探索・教師全規則を同一にすることは分ける。既忠実Web751186 native経路のK64/K800結果でC++総生成効率を代弁しない。

優先順位は181の薄checkpoint削減→新独立CPU教師/learner接続を主とする。183のNN0静的設計・人工3handle/8項目mockを有限受入れ。既Rust Registry worker各4/8gameと177共通GPU maxB8 queueを最大1案とする。実NN/GPU/game0であり実効batch/RAM/教師率は未測定。既cache即時listingでC++extension未確認はhost全体の不存在証明ではない。compile/download/newmodel/NN/GPU/game0、181 writerと科学jobを妨げず、183全文待ちgate0。今枠にこのSigma型GPU実生成を配分済みとはしない。181は12:25science終了予定、残りは保存/12:37:38重開始停止もあり、通常は次枠実測候補。181が早く引渡し、183準備が有限に成立し、直前所有/資源/残20分以上の終了余裕がある場合のみ統括が新現在配分を決める。ここでGPUjobを自動起動せず、次枠計画だけで現12:47:38を延長しない。

次の実測候補を以下の単位で定める。

- CPU worker最大3（core2/4/6）＋共有GPU provider/broker管理1（core0）、CPU4logical/RAM8GiB/VRAM6GiB/job30分を維持。game数をprocess数にしない。各gameの探索は1pending leafのみ、game間を多重化してsameKの木を独立保持し、virtual loss/多leaf同tree/PCR/solver/TT追加をこの構造比較へ混ぜない。
- 第1小比較は同fresh24game/モデルd790/K64/tau/lineage条件を結果前固定し、CPU3 heldsession基準とGPU共有maxB8でactive game総数3/12/24を比較する案。queueには全game ID/generation/tokenを保持し、返却取り違え・取消・遅着・待ち上限をtypedに扱う。active24は3worker各8gameをpoolで管理、同時24OS processにしない。steady/cold/init/輸送/保存/尾部を全jobへ計上する。最終K/π/z資格/全予定fault/censoringを保ち、実効batch分布・queue待ち・batch-fill・有効Rpolicy/Rz/Rjointとgame/secを使う。
- 177/176はprivate Torch dynamicB<=8までを有限確認済み。B16/32又は48activeは、上記最小方式で利益が残りメモリheadroomと異種入力parityが成立した時の次拡張案で、現在readyや効果を仮定しない。原ONNXbatch1と実GPU batchを混同しない。2048game/1024batchを複製しない。
- 将来実runの初期見積はCPU対照上限300秒、GPU各mode上限300秒・GPU累計900秒/1job30分内、RAM全体6GiB guard5.5GiB/新保持128MiB程度を既予約から割当てる案。全3mode/全24game完走や速度利益の保証ではなく、打切りzunknown/全attempt費も残す。NN/量と実最大arena保持は183が上界と実装費を見積り、実配分時に固定する。既GPU学習はこの検証で0。

採否はCPU単入力/3arena maxB2の結果から推定せず、同条件・同Kの実生成で有効教師率が増え、合法性/視点/lineage/教師品質が保たれ、queue/輸送/RAM/VRAMを含む総費に利益が残るかで決める。CPU側MCTS/特徴・合法/BFSが支配的ならGPUbatch追加だけを続けずCPU最適化へ戻す。原C++実行がcache内に用意済みなら版/model/探索設定を別bindingした比較候補、未用意なら未実測と記し巨大新移植・依存取得を今枠に混ぜない。構造比較/全Sigma C++方式/棋力NI/学習価値を別結論にする。

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

181新27K800の本人速報:old/new根対応を有限保持、new/old中央値.961216/.879079/.958675、採用<=.90は1/3で限定条件未達。new/JS1.299314/1.136611/1.165635、24新lineage productionは原選定どおりCPUJS。利益時のみ6K64比較は全NOT_STARTEDとして保持し、速度診断の追加反復0。内部checkpoint800→1/応答約8→4MBの削減が生成利益や棋力を証明したとはしない。182独立180支持は必要7Gitblob/停止backupを統括受入れclose、後着metadataのGit版誤指定失敗は科学と別に保存。

183の実装見積45〜75分、4mode測定上限20分に最速CPUJS採用対照の任意5分と保存費が追加される。全比較の実生成は次枠候補として保持し、現在の残枠で完了すると約束しない。partial batch B3/5/6/7は177で未測定なので実モデルを使う前に有限parityを予算内で扱う。各mode最大307200sampleは原177/176capと別の私有run予算bindingを要し、黙って上限をresetしない。新GPU予算/自動起動0。今枠に前倒しする場合も181停止引渡し後の新有限配分として、薄実装の準備と実生成検証を分ける。

181科学停止・保存引渡しを受領。新24GOAL/1353適格行をCPUJSで195.29244秒/6.9281行秒、旧新train2260/200stepで原val π/z改善・新val π改善/z悪化を保持。184criticへ保存独立教師/損失検算（NN0/static120秒/新2MiB）を配分。183受入れ設計の実GPU比較は次枠、今枠185experimentへ最小gamepool/brokerのNN0実装準備35分（script180秒/新8MiB既experiment内）だけを配分する。実生成倍率/実partialGPUparity/多木RAM未測定を維持し、実GPU検査をこの準備へ自動追加しない。学習の次配分は184のvalue悪化裁定と実既lossから選ぶ。

184速報を部分採用。独立1353行算術/共有RuleA24局再生は有限支持、原val/newvalの損失値はsaved receipt bindingで新forward再認証0。新val πCE2.571901→2.391096改善、zMSE1.663258→1.951053/総4.235158→4.342149悪化を保つ。181継続checkpointを既定へ自動置換せず代替候補として保存し、176checkpointを比較基準として保持する。正式な新lineage棋力や多様性因果は未確定、次の学習配分は旧新validationのπ/z別結果で選ぶ。production195.29244秒の6.928072行秒と全7guardian390.744963秒の3.462617行秒、prep等unknownを分ける。184最終source/停止binding報告を待ち、185NN0準備継続/全稿待ちgate0。

181/184最終有限受入れ。原181必要6Gitblob/packSHA、独立184必要8Gitblob/currentexactと自己停止backupへbindし、両課題を統括引継closeする。全24/1353行・K64/π/z/P2/split・27K800原選定を支持するが新forward/all-deep/棋力認定0。旧新val合算総loss3.778808→3.614792の改善に対しvalue1.232192→1.269360は悪化。181のcheckpointは代替として保持する判断を確定、pooled totalでvalue悪化を隠さない。現在実施中は185NN0薄gamepool準備、12:15科学終了/12:32提出の範囲で結果・不足を待つ。
