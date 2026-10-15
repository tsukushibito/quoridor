# 零在庫近似の速度優先有限結果（406）

同一真正image `43971e3b…` / BUILD `272406e0…`、source Git `7aa63d74…` で、NNUE BEST43と固定D(0,8tanh)を別stratumとして比較した。双方Control・LMR OFF・PVS ON・TT1,048,576、深さ8・各4M nodes、時間上限なし、diagnostics/depthcallback OFF。実入力は指定された元対局4prefix（残壁6/4/2/0）の完全履歴再生である。null→4→0→0→4→null、各4root cold/warmの96 calls・48sessionsを一度だけ実行し、追加sampling・補充・Search再演は0。

**72 COMPLETE＋24 UNKNOWN、実137,938,286 nodes（上限384M）**。UNKNOWNは残壁6枚rootの全24callで、4M/NodeLimit/completed6/target8。未完成を完成D8へ読み替えない。同条件二反復はrequest/root/status/depth/valuebits/action/PV/全保存work一致。全96のactual settings、合法返却、PV・親と完全history復元、元journal/result対応、全12operationの原PASS/cleanupとfresh process absenceを確認した。これは全callが要求深さを完成したという意味ではない。

## setup/drop込みwholeと探索仕事

wholeは8 callsに加えてsetup、session reset/teardown、journal等を含む各pass全体の二反復中央値。時間比は同仕事speedupではなく、評価木・仕事・固定費込みの有限観測である。

|評価|設定|whole秒（2pass中央値）|なし比|nodes（16calls）|通常評価|差分更新|近似終了|COMPLETE/UNKNOWN|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|nnue|なし|14.351203|1.000000|23,851,142|16,921,020|23,826,868|0|12/4|
|nnue|開始時固定≥4|14.221805|0.990983|23,447,350|16,534,388|23,308,010|115,066|12/4|
|nnue|全root許可0|14.227260|0.991364|23,331,236|16,496,066|23,190,120|140,618|12/4|
|distance|なし|6.211742|1.000000|22,908,960|16,738,286|0|0|12/4|
|distance|開始時固定≥4|6.905561|1.111695|22,245,524|16,240,478|0|289,624|12/4|
|distance|全root許可0|6.923400|1.114566|22,154,074|16,214,384|0|313,654|12/4|

NNUEのwholeは約0.9%短い一方、固定Dでは約11%長い。n=2・固定順序・この4rootの結果で、一律高速化や最適閾値は支持しない。TT retained bytes/generationはgaugeなので合計workへ加算しない。上表の通常評価・差分更新・近似終了は保存scalarの別分母であり、物理NNUE forward件数や部位別時間ではない。

## 局面別cold/warm

下表の時間はSearch呼出全体の二反復中央値(ms)。通常評価・差分更新・近似終了、body/journal込み時計、二反復の実値、status/stop/value/PVはresult.jsonへ保存した。coldの実効mode切替に伴うTT/history clear等も呼出全体へ含まれる。

|評価|設定|残壁|depth cold/warm|Search ms cold/warm|nodes cold/warm|近似終了 cold/warm|
|---|---|---:|---|---:|---:|---:|
|nnue|なし|6|6/6|4761.652/4729.265|4,000,000/4,000,000|0/0|
|nnue|なし|4|8/8|2336.728/2215.845|1,950,370/1,890,538|0/0|
|nnue|なし|2|8/8|31.749/29.413|42,437/40,856|0/0|
|nnue|なし|0|8/8|0.551/0.467|717/653|0/0|
|nnue|開始時固定≥4|6|6/6|4783.472/4737.605|4,000,000/4,000,000|0/674|
|nnue|開始時固定≥4|4|8/8|2253.986/2128.999|1,845,465/1,793,547|28,779/28,080|
|nnue|開始時固定≥4|2|8/8|35.553/28.964|42,437/40,856|0/0|
|nnue|開始時固定≥4|0|8/8|0.724/0.470|717/653|0/0|
|nnue|全root許可0|6|6/6|4807.800/4756.659|4,000,000/4,000,000|0/674|
|nnue|全root許可0|4|8/8|2241.129/2152.507|1,845,465/1,793,547|28,779/28,080|
|nnue|全root許可0|2|8/8|14.400/10.028|13,719/12,838|6,430/6,318|
|nnue|全root許可0|0|8/8|4.975/0.039|25/24|14/14|
|distance|なし|6|6/6|1959.559/2324.337|4,000,000/4,000,000|0/0|
|distance|なし|4|8/8|829.203/803.189|1,692,514/1,676,078|0/0|
|distance|なし|2|8/8|17.940/15.017|43,132/41,421|0/0|
|distance|なし|0|8/8|0.316/0.321|682/653|0/0|
|distance|開始時固定≥4|6|6/6|1944.087/2396.826|4,000,000/4,000,000|0/839|
|distance|開始時固定≥4|4|8/8|1175.995/1088.719|1,541,949/1,494,925|81,024/62,949|
|distance|開始時固定≥4|2|8/8|18.118/16.121|43,132/41,421|0/0|
|distance|開始時固定≥4|0|8/8|0.312/0.276|682/653|0/0|
|distance|全root許可0|6|6/6|1947.479/2393.053|4,000,000/4,000,000|0/839|
|distance|全root許可0|4|8/8|1158.804/1110.283|1,541,949/1,494,925|81,024/62,949|
|distance|全root許可0|2|8/8|19.070/10.463|20,552/19,562|6,027/5,960|
|distance|全root許可0|0|8/8|5.199/0.031|25/24|14/14|

閾値4は残壁2/0のrootで実効OFFとなり、なしとstatus/depth/value/action/PV/全workが一致した。rootの許可固定が意図どおり近い終盤を通常探索に残すことを確認した。残壁6/4では0と4が同じ有効方式となり、閾値数値そのものを別方式にしない。近似終了件数は全反復と未完了の最終反復を含む累積で、完成深さ6だけの費用へ戻さない。

全root許可0の残壁2/0ではnodesや通常評価は減るが、時間は一様には減らない。例えばNNUE残壁0のcoldは約0.551ms→4.975ms、warmは0.467ms→0.039ms。初回切替・初期化とwarm再利用を含む境界の違いがあり、nodes減だけでwhole利益を認定しない。固定D残壁4は約1.69M→1.54M cold nodesへ減っても、約0.829s→1.159s。距離fallback、切替、探索仕事と呼出費を含み、孤立したTT clear/BFS/近似式等の時計は未記録なので原因別費はUNKNOWN。

全root許可0の残壁2/0では、今回のroot actionは同じでもvaluebitsとPVが変わる。正常終局の2を非終局近似の1へ置換して読ませる例もあり、近似入りcompleted8はその評価方針の名目深さであって、通常全幅depth8やゲームのexact WDLではない。真のgoal/threefold優先を消したという意味でもない。

## 保存52fixtureの誤判定

保存ラベルのみを照合した5,680 active小盤面状態で、Win→Loss 324、Loss→Win 296。Win→Win 3206、Loss→Loss 1854。元52fixtureにはDrawラベル0で、その誤判定は未観測。式自体は±1だけでDrawを表現しない。元WDL solver/合法辺/rankの再実行は0。小盤面board-onlyの照合を9×9・実履歴・訪問分布・棋力へ一般化しない。

## 費用・停止・判断

元speed sequence outerは186.226594642s、12pass whole合計は125.681939528sでnested値をouterへ足さない。元software二jobの非重複outer合計は116.416451455s（FAILED 9.486728284sを含む）。source/LLM/admin/保存解析を含む全費用、物理NNUE forward、部位別時計、continuous RSS peakはUNKNOWN。実TT本体は各session83,886,128BでRSSではない。family4GiB/GPU0の実guard内で完了した。

原BUILD v2のE0063/FAILED、既存fixtureへNoneを加えた別修復、guardian returned NULLとpersisted pending/attempted等の違い、初回collectorのmanifest生成前の読取仮定、SHA入力のpreflight拒否、Rootのclose owner fence拒否を保持する。最初の失敗を成功へ書き換えず、真正image作成後の科学実行は今回の元96だけ。元journal/RAW・入力・モデルを保全し、旧trialへ数値を遡及しない。

実native/sequence readerSTOPは2026-10-15T03:39:18.372901Z。49個の元native/guard/outer identityをfresh absent/different、directwait/reap、handles/TMP/lease解放として確認し、407の通常作業へ境界を通知した。保存collectorも別STOP/owned[]を保持する。

**研究optionを既定null/OFFのまま保持し、今回の有限結果から一律高速化・棋力・製品/生成既定採用は決めない。** 人間が速度結果を見て次を判断するまで対局・追加閾値比較・新学習は発行しない。407の方法選択は別差分のsource/softwareであり、この406の式・image・入力・結果を変更しない。mixed/learner全prep/pipelineと323 USERPAUSE、defaults/models/weights/seals/oldfits96/foreign変更、旧RAW/FAILED/費UNKNOWNを維持する。
