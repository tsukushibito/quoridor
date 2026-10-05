# Dclip／Dtanhと凍結NNUEの同100ms診断（249）

2026-10-05 frame20。全8slotは終局し、Dclip対NNUE・Dtanh対NNUEともNNUEは2勝2敗。340採用手は親の完全parse・generation/key/history・合法Action検査終了まで100ms以内、late／UNKNOWN／node32768到達はいずれも0だった。一般棋力・NI・最高研究goalは未認定。

## 結果前条件と範囲

旧242の2family・opening8/16ply・seed/prefixを参照した同prefix再測定。2family×色交換×Dclip/Dtanhの8slotを新規登録し、全局を今回実行した。旧242勝敗の片側流用、成功補充、旧testlabel／正式173の再読・学習はない。family0順clip-P1,tanh-P1,tanh-P2,clip-P2、family1は逆均衡。後半の開始判断は残clock/cap/物理条件で、勝敗による選別はない。

凍結228 NNUE（576 BEST2000）12193 LEf32/48772B tensor SHA b81792d5ba00c6d79b58cada2fc81d84ea822db48c04420b4e269fb9b71841b3、scale SHA68f8b43a0e4408a1546f8fa2652ffdf21f1f7bdcfbac9a25a86ac666b27aa4eeとactualSTMは両条件同一。NNUEの出力数学・探索は変更しない。Dはa=.06038215201109912,b=7.925687690687516。ds=f32(distance/80)、diff=f32(ds_opp-ds_self)、u=f32(f32(a)+f32(f32(b)*diff))を共通にし、非terminalだけclip(u,-1,1)対f32(Math.tanh(u))とした。winner±1／200ply draw／noLegal0が先。tanhは|u|<1を含む全非terminal値とMath.tanh費・terminalとの相対校正を変えるので、飽和解除だけの介入ではない。f32tanhの端点±1も可能。

双方rootbest-first stable全合法、leaf-fastpackage、clone-parent、FT-delta、TT0/noise0/policy除外0、nodecap32768、内90ms／親100ms、未完depth破棄。受信後monotonic検査が採用基準で、timer callbackだけを期限内証拠にしない。Node-hosted nativeでRust/Wasm/Sigma公開C++を代表しない。rootmean教師精度はminimax leaf真値・棋力を代弁しない。

## 全slot

|slot|family|D|NNUE側|status|NNUE結果|手数|
|---:|---:|---|---:|---|---|---:|
|1|opening0|clip|1|TERMINAL|L|46|
|2|opening0|tanh|1|TERMINAL|L|46|
|3|opening0|tanh|2|TERMINAL|W|50|
|4|opening0|clip|2|TERMINAL|W|52|
|5|opening1|tanh|1|TERMINAL|W|33|
|6|opening1|clip|1|TERMINAL|W|51|
|7|opening1|clip|2|TERMINAL|L|31|
|8|opening1|tanh|2|TERMINAL|L|31|

## 探索・時計と同入力対応

以下は異なる到達Stateを含む集計で、depth/node/NN比を同仕事の速度・棋力因果として扱わない。完成depthには強制終局での64などもあり、平均深さを一般的なhorizon認定にしない。

|D条件／engine|採用手|processed|NN／D eval|terminal|nodecap|最小時計余白ms|
|---|---:|---:|---:|---:|---:|---:|
|clip/NNUE|90|185749|138715|3609|0|1.429020|
|clip/distance|90|268351|193313|5765|0|6.449536|
|tanh/NNUE|80|164755|129527|2193|0|1.220633|
|tanh/distance|80|240691|186271|3794|0|5.055427|

Dの変換前|u|>=1はclip18230/193313=.094303、tanh24907/186271=.133714。これはtanh出力端点の割合ではなく、異なる到達局面で実行した非terminal評価の入力統計。D terminalはclip5765/tanh3794として別記録。全leafの再forward／全extrema由来の追加記録は行わない。

sameboard+STM+RuleAの全count-historyが一致する入力115組は全て実prefixも一致した。

|engine|一致入力|共通完成depth|値差最大abs|共通depth Action差|最終Action差|
|---|---:|---:|---:|---:|---:|
|NNUE|57|150|0|0|1|
|distance|58|275|0.2113248706|6|1|

NNUEの共通depth150件は値・Action差0。最終Action差1は完成depth差を含む。Dの共通depth275件でAction差6、最大値差.211324871。全exact child／等値argmax集合はNOT_RECORDEDであり、旧failsoftをexactへ昇格しない。Dの手選択が変わる有限証拠と、相対WDL2W2Lの一致は両立する。少数同prefixの勝敗一致からDclipの非terminal飽和が無害、またはtanhが公平な基準という一般結論は出ない。

## 有限確認・費・停止

actual私有sourceに対するpreflightで旧clipとの共通完成depth値・Action／NNUE出力をabs1e-7+rtol1e-7で有限照合し、248 clip/tanhの同入力194rootchild値も対応した。actual protocol6fixtureはvalid・stale/generation・late・incomplete・EOF・合法validation overshootを確認し、validation後100ms超の完成応答は不採用。全Torch/teachertruth/deep argmax再認証ではない。

|job|実開始→終了UTC|NN|guardian wall s|peak family RSS B|
|---|---|---:|---:|---:|
|2026-10-05T01:46:56.027991+00:00|2026-10-05T01:46:56.027991+00:00→2026-10-05T01:47:13.818880+00:00|156272|17.821079367|357515264|
|2026-10-05T01:45:29.945283+00:00|2026-10-05T01:45:29.945283+00:00→2026-10-05T01:45:30.961840+00:00|5500|1.016560590|241938432|
|2026-10-05T01:48:49.839462+00:00|2026-10-05T01:48:49.839462+00:00→2026-10-05T01:49:03.101056+00:00|111970|13.261598019|320421888|

全3 model-scienceを一度ずつ実行、known/charged NNは273742、guardian wall32.099237976s。全exit0・子wait／記録PIDtick不在・背景cleanupComplete。family controller wholewallは17.772592401/13.183118922s、ready初期化31.060463/31.506827ms。guardian/controller/background/queueは重複を含むため排他的な総費へ単純加算しない。

background preflightは新ROLE250 bindingと静的foreign解除を制御待機し、新science01:45:29.945283で開始。旧ROLE247 stopped/nextnullを新freeへ代用しなかった。source/preregister-v2採択と測定効果は別。LLM/通信/一部管理費は未計測・UNKNOWNで、作為的に0へ補充しない。最初のNN0保存集計は継承affinityの単一Pythonとして記録、以後の保存算術はCPU2へpinし、成功集計を置換再runしない。source停止正本scientific-stop-v1.json、全attempt/guardian/backgroundを保持。

旧236/240/242の科学・失敗・unknown・個別期限・予約は不変更。旧229最終checker NOT_RUNは保持し、今回owner有限集計を独立PASS／最高棋力へ読み替えない。新科学3job/600s/1mNN、CPU2single/GPU0/RAM896MiB guard、8MiB予約/7MiB保存guardは元配分内。必要Git/index不変更・小pack3member復元・Beads close/backup receiptは管理保存へ記録。

## 次の最大1判断案

現基準は保持し、新value／基準へ自動昇格しない。保存したDの共通depth Action分岐6件を248の既exact資料と照合できる範囲で、clip同値／terminal校正／完成depth差へ区分する静的対照を次候補にする（新forward/arena/学習を自動開始しない）。費用は保存済み小表の照合、判別力は手変更の出所の限定にあり、同wall一般棋力を証明しない。新teacher/history方針や探索costの再配分はこの資料と独立裁定を受け統括が選ぶ。
