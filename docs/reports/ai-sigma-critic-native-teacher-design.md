# 178 native教師の品質と生成効率の独立設計裁定

2026-10-03 critic、quoridor-4lc.178。受領09:07:57 UTC、ready/show goal+self・pauseなし・本人割当を確認し09:08:47.422339 claim/静的実開始、統括へ報告。親frame12は08:47:38→12:47:38、重開始12:37:38/監督12:42:38/monitor12:45:38を保持。writerは178 data域と本報告のみ。176/177/旧source・モデル・親・運用はreadonly、新NN/forward/session/Chrome/game/build/GPU/train/取得/委譲0。

**176の初期CPU生成・学習接続を支持し、最大1具体案として、教師資格別の行数と全attempt費用を併記する台帳を推奨する。** 完全な教師品質保証や178全文承認を生成の入口に追加しない。効率化の比較はこの台帳と固定Kの最終root対応で判断し、学習fit/24game・速度をSigma非劣性へ置換しない。

## 比較する分母を固定する

全dispatch/生成予定game・探索attemptを残し、型付き失敗・打切り・中止を成功補充で消さない。次の数を同じjobの総wall時間で割る。

| 分子 | 最小資格 | 目的・限界 |
| --- | --- | --- |
| Rpolicy | 非終端の完成root、合法mapping/訪問分母/有限π/署名対応 | policy CEに使える行。終局z未知でも資格を持ち得る |
| Rz | 真の終局結果と正しいsideが対応したvalue行 | z教師。policyの有無とは別 |
| Rjoint | 同じ行がRpolicyとRzの両資格を満たす | π＋z学習の主生成率 |
| Rpolicy_zunknown | policy資格があり終局z未知 | MSEから除外、policy用途は別記 |
| Rall / Rfailed | 全attempt / 資格を満たさない行と理由 | 成功だけの分母へ選別しない |

総job時間にはモデルinit/warmup、入力生成・合法履歴、特徴生成、探索、NN、輸送、記録、打切りcleanup・終了保存を含める。共有GPUサービスや常駐sessionのinitを複数jobへ按分するなら規則と未按分総額を併記する。kernel/API時間だけ、成功局だけ、最終row書込だけを分母にしない。包含・並列区間の時間を足してCPU総費としない。

合わせてraw rows、完全state署名ユニーク数、特徴648＋合法maskの重複数、game lineage数、opening長/先後/newply別の件数、policy-only/打切り率、出力bytesを示す。『有効』は上のschema・機構資格であり、最強教師や独立同分布の局面数という意味ではない。重複行を黙って削除してraw速度を有効速度へ読み替えず、圧縮前後も同じ資格分母を使う。

## K64、教師値、行動を分ける

非終端rootの固定K64ではrootN64/edge訪問和63を期待し、π(a)=Nedge(a)/63を使う。rootNNの初回評価を含むrootmean=root_valueSum/64をedge63で割り直さない。Kをroot visitとして保持し、terminal-noNNを『推論64回』へ換算しない。started/returned/discard/startupは別counterとし、未完了Kを64達成へ補完しない。

rootNNは探索前の根のvalue、rootmeanは根のbackup平均、leafNNは葉に対応した別sample、zは実際の終局結果である。source/side・視点・値の由来を別fieldにする。leaf/rootNN/rootmean/zを同じvalue labelに混ぜず、rootmean auxiliaryを入れる場合は採否とweightをデータ前に固定する。追加root教師forwardを行わず初回rootNNの保存を再利用するが、first_NNが根を指すことを対象adapterの有限確認で対応させる。

値はz_p1∈{-1,0,1}とz_stm=(P1手番なら+1/P2手番なら−1)×z_p1を分ける。正規drawのみz=0。上限・infra・中止・不明はz=null、value loss mask=false。勝者不明をdraw0にしない。真の終端rootはπ訪問を作れない場合があるのでπ=null/policy mask=falseを保持し、ゼロ訪問をuniform/prior教師へ置換しない。

訪問πと実行actionは別。温度1の最初16**新ply**では訪問分布からseed付き抽選、その後はargmax/既firsttieを保存する。openingの12/13plyを数え込んでランダム区間を短縮しない。argmax actionや抽選onehotをπの代わりにCEへ渡さない。新ply・temperature・seed・抽選action/orderを記録する。温度は行動経路の多様性を変え、teacher K64の探索分布を高強度教師へ保証するものではない。

0/4/5/12/13ply循環、24gameという少数開始は動作/教師入口の有限確認として支持する。少数prefixの局面側優位、短いゲームへの偏り、共通初期状態やargmax期の反復があるため、局面多様性・通常対局代表性・強教師分布は未証明。勝率・rootmean・短期終局で入力や教師を有利に選別しない。

## 漏洩とmaskの最小確認

game-lineage hashを結果を見ずsplitし、同gameの全手・再export・resume・同じ生成物のbackend別複製は同じlineageに置く。単に新game IDを付けた複製を別validationへ入れない。共通prefixからの別gameは異なるlineageでもstate/featureが一致し得るので、game splitだけではstate独立validationにならない。完全state署名（side、壁残、合法history/反復、prefix/ply等）とfeature＋legal-mask重複を報告し、validationを『新gameに対する教師fit』の範囲へ限定する。全crossgame state分離を初期生成の必須gateにしない。

173正式holdout198game・旧正式入力は学習、教師選定、学習ハイパーパラメータ選定へ転用しない。将来arenaの入力/lineage/seedは学習と別に結果前登録し、arena結果から都合の良い入力・成績を置換しない。

Rust209の合法Action→canonical136は実着地とsideを持ち、P2のvertical reflectionを特徴/方策/合法maskへ一貫適用する。直進jumpは隣接pawnを越した着地を確認し、斜めjumpや壁の向きを混同しない。合法136のmaskにpi massが収まり、非負訪問の和63、対応先が重複しないことを保存する。maskなしでCE学習すると、合法targetでも違法logitをsoftmaxの分母へ含める学習条件になる。masked/unmaskedのどちらを採るかを学生loss契約で明示し、後から比較時だけ変えない。

小NN0mockはP2 straight jump Action31→136index0、h-wall81→64、v-wall145→128、訪問42/14/7→π2/3・2/9・1/9、P2 z/rootNN/rootmean符号、未知z、終端root πなし、136 permutation involution、同lineage split不一致を確認した。illegal mass/rootN64をπ分母に使う誤り/P2符号/署名/edge数/打切りdraw化の6不正caseは拒否した。これは算術/schemaの人工確認で、全局面のRuleA/斜めjump/実176adapterを再認証したものではない。実準備では既160のP2・壁・jump fixtureの必要部分と新row1件程度へ対応させればよく、全局面完備を入口にしない。

## final-only CPとGPU branchの解釈

固定Kの最終CPだけを配送する案は支持する。MCTS選択・PUCT/FPU・firsttie・backup・合法順・root初期NNと取消event drainは保持し、正常完了Kのroot edges/rootmean/actionと既modeを小同入力で対応する。early CPがなくなるためfirstCPの意味は『最終Kの配送』へ変わり、500ms採用や旧firstCP速度と同列に比較しない。cancel時の部分K・未回収NN・typed failureを成功Kとして返さない。

旧native-baseline/engine.cjsではprogress/cpShapeでroot_edgesを毎sim作りemitし、referenceのonCompleteもCP生成へ入る。final-onlyでJSON/IPCだけ止めても、内部root_edges再構築が毎sim残る可能性がある。その場合は改善を配送部分に限定し、内部計算も消えたと主張しない。176実sourceは今回読取時点で未生成だったため、薄wrapperでの実反映・取消・数値最終root対応は不足としてowner成果へ渡す。実装開始をこの確認待ちにはしない。

同Kの品質対応はrootN/edge/π/action/rootNN/rootmeanとNN/terminal-noNN量の有限照合で、同wall棋力とは別。前後modeの総費/Rjoint/jobtimeを比べ、K低下や失敗行の排除だけによる速度を品質保持改善としない。

GPU batchingは複数独立searchの各1pendingをまとめる候補と、単tree多leaf/virtual loss/backup順変更を分ける。前者でも結果をsearch ID・generation・token・sideへ正しく返し、各treeは依存するNN応答を受けてから次探索へ進む。batch1の8要求をbatch8と呼ばない。最大待ち時間/実batchサイズ/padding/queue/転送同期/CPU前後処理と総生成費を記録する。未測GPU性能をCPU初期生成のgateにしない。

GPU数値差が小さくてもPUCTのtieや近接scoreでpath/action/教師πが変わり得る。174の5固定入力ではCPUORT対torchCUDA policy差最大5.7220459e−6/value差3.5762787e−7、batch1転送同期込みCPU中央値3.5707745ms/CUDA2.100652msという有限観測だった。全native自己対局倍率、真batch、教師品質対応、Sigma NIを認定しない。CPU/GPU教師を混ぜる場合はmodel/source/providerと差の観測を残し、数値tolで離散path差を救済しない。

## 既成果の射程と停止・引渡し

160は保存5根/K32 edge31のmapping/mask/P2/value視点・group validation入口、z/leafは欠測。162は4train/1validationの20step toy、checkpoint/reload/既ONNX数値parityの学習入口で、棋力や本PV構造完成ではない。173の198holdoutは95W103L・不確かとして保持し、今回の教師データへ混合しない。これらを再実行せず必要scopeを参照した。

支持: 176少数CPU生成→資格row/export→小learner→別診断arena、固定K final-only配送。追加の全role承認gateなし。

不足: 実176sourceへの反映、実datasetの終局/重複/資格率、final-only総費、GPU batchおよびbackendによる探索対応・有効教師量。小schema mockやparityをこの実測へ格上げしない。

最大1提案: 上の資格別teacherrows/全attempt総job台帳を結果前固定し、品質削減と配送改善を判別する。176の初期実生成を止めず、小fixture/新row有限確認で不足を具体化する。

資源はCPU0単1/static60s/RAM512MiBguard448。mock .001077426秒、RSS peak16,609,280B、PID終了/currentidentity不在、source/子停止をstatic-stop.jsonに保存し09:12速報でcoordinator経由hyp177へCPU0静的終了を通知した。以後は必要保存/小Git/backup/報告管理だけで、GPU model＋3arenaへ追加CPU5を作らない。これら短管理も実CPU0jobなのでownerは必要時同coreで順序を調整する。active LLM数をgateにしない。

直前保存forecastは旧未知88,190,086Bを減額せず、既scope実量4,308,992B＋新scope2MiB=94,596,230B<critic112MiBguard。親追加予約0。科学新実行0。必要小Git復元/Beadsbackup/最終配送は178 handoffで示す。受入れ/closeはcoordinator、goal/他者close0。
