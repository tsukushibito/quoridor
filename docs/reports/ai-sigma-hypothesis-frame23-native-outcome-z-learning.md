# 真正自前終局zのD保持NNUE学習（298）

登録した一学習は成立した。旧285の完整576familyをラベル非依存のsalted UID規則で432 train /144 selectionに再分割した。対象は既見コーパスの探索的selectionであり、未見独立評価ではない。全19536行中train14803、rawselection4733、state・完全history literal・STM f32入力OR除外は0、zeroeligibleは0だった。575 GOALと1真正RuleA drawを保持し、drawはnative終局処理でも0を確認した。旧公開0043、開封済み対局、旧validation/futureは学習allowlistに入れていない。

QF1疎312両view＋D保持H32、route4 zero、raw D=(a0,b8)、旧train-only尺度、seed19080311、Adam1e-4/WD0、family一様→row一様、7813×128=1000064 seenを固定した。10点は0/1/5/20/50/100/200/1000/4000/7813。tensor metadataとP1P2→STM入力を検査し、子cacheを改変せずhash-bound shard manifestとRAM concatenateを使用した。新dense diskコピーは作らなかった。

|点|train family z MSE|selection family z MSE|
|---|---:|---:|
|初期D|.615387488|.660867274|
|200|.600717974|.652236350|
|1000 BEST|.280252574|.585894418|
|4000|.005187532|.747894928|
|7813 LAST|.000319466|.851886855|

selection constantは.999467263、train-only family constant値は.0216037281068。初期DよりBESTが低い一方、末期fitはselectionで退行した。teacher-rootmean版、公開z版とはcorpus・分布・教師・family重み・選定目的が異なり、今回の改善を純target因果、独立転移、同時間棋力に読み替えない。

一fitは21:48:02.797336→21:48:14.165554 UTC、実1195424NN/1234496processed、guardian11.393525秒、sampled family peak988413952Bで全wait/currentidentity不在。model9.879251秒、background14.831875秒は包含spanなので加算しない。保存initial/BESTに対する有限native parityは312NN（maintained CLI180、Torch24、既停止comparison-only SIMD CLI108）でPASS。P2/STM distance bits、full/delta、SIMD、親復帰、draw優先を確認し最大差1.1920929e-7。main CLIのSIMD field欠測を旧比較binで補った範囲であり、恒常別数学入口・新buildを追加していない。

第三jobの追加saved-scalar再集計は失敗した。私有wrapperがcache.loadの戻り値(binding,rows,x,distance,labels)を誤って解釈し、IndexErrorで算術前に停止した。実model/forward0、元source/log/exit1と50000processed予約を保全し、再実行していない。成功した学習時selectorと失敗した追加検算を分離した。MAX3は全消費、実NN1195736、保守予約NN1196424/processed1287496、科学command合計14.043766秒。NN0管理/LLM/readの未測定分はUNKNOWNで、科学費と包含spanを混同しない。

観測候補は元trainerの事前argmin規則どおりBEST1000で固定した。weights SHA1f8d8c28、manifest3177ff54、initial ec4167、scale175f077。candidate-freeze-v1.json SHA5768486550449fda256f70de2196bc1c3e6831ec52828b984a19eacbe673e0b6は成功fitの保存freezeをmanagementでpath/hash束縛したもので、第三jobの算術成功ではない。source/modelreader/selector停止SHA575f3df4、全scheduled scalar/roworder/weightsを別metadataに束縛した。保守Tseen全14803とALLrawV4733、公開baseline T67937＋ALLrawV19965のinput-only参照を300へ渡した。公開history欠測は完全非露出保証にしない。新299のラベルは298では未読である。

現役接続の変更はmanaged WTのcache.py/common.py/train.py/test_sharded_cache.pyに限定した。strict shard reference、明示checkpoint/native-only artifact mode、同forwardのscalar/weights保存、sampling counts、explicit oldscaleの直接検査を追加し既defaultを保持した。変更4PythonのRuff format→check/lintとNN0 fixture4件はPASS。readonly residual_model.pyは元WT bytesをgzip保全・復元照合した上でmain SHA2104e17へ一致配置し、数学は変更していない。main書込・Git/indexは統括のみ。managed-source-diffと19member科学source archiveを停止handoffした。未使用route scaffoldをmainへ移す必要はない。追加算術のAPI欠落は将来最小tuple/type fixtureが必要で、今回のselectorの独立検算PASSに付け替えない。

優先する次判断は、300の固定新96family一巡でこの凍結候補のz転移を測ることである。既許可の評価をD利益やmain統合ACKで止めず、公開候補/D/constantと同family・同maskで区別する。その結果で次最大1を選ぶ。独立z転移を支持するなら、凍結モデルを機械固定prefixで同完成depthのleaf/Actionと費へ接続する小対照を優先する。MSE利益だけから同wall強さへ昇格しない。転移が支持されないなら、今回のlate退行と競合するfamily量・表現・履歴・教師分布を保持し、量に対応した露出と位置付き経路/壁効果を同候補として再配分する。小selection利益を十分量のgateにしない。

振幅一律縮小は297でrow/groupの推奨gammaが反転し、普遍原因の根拠が弱い。高K/seed教師安定性はpolicy終局z自体の真値保証とは別に探索教師の質を問う有力保留である。位置付き経路情報はDAG4の一条件不支持で一般否定できないが、追加cache/壁更新/native葉費の測定が必要。今回の96familyはpilotであり十分precisionの証明ではない。群差の分散と目標精度に応じた必要family数は独立評価後に見積もる。次の同depth接続は24固定prefix・2評価器程度なら最大1000NN程度、準備/検証10–30分・CPU30–120秒・保存2–4MiBを初期概算とし、native input/action/historyの意味差とactual capsを結果前に具体化する。新実装・forward・対局をこの報告から開始しない。

保管は298新32MiB内でsource/asset現在実量＋必要Git/tmp/archive/metadataを包含して管理した。初回freeze入場は保存済みcheckpointを残future8MiBとして重複計上してguard拒否（科学spawn0）し、実currentへ一本化したv3を別保存した。旧UNKNOWN128MiB、元旧run費・caps・原失敗・開封済みprotocolは不変更。必要保存manifest/source patch/curve/weights/scalars/failure/stopsを正本scopeから参照し、親goal最高棋力は未達のまま。
