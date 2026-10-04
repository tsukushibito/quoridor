# critic217：適合・汎化差の有限独立裁定

同一train96/validation24、4653/1248行、rootmean STM、元game等重みで、**200stepの適合不足と400stepの汎化不足が共存する**見方を支持する。400stepのtrain適合からQF1情報・容量の全面不足は導けず、validationで距離を超えないことから教師不良・history・分布の一原因も決められない。fresh testよりこの差を判別する現在の優先順位を支持する。

|方式|train gameMSE|validation gameMSE|validation rowMSE|
|---|---:|---:|---:|
|train定数|.7243203911|.6787804677|.6660051546|
|train-fit距離D|.4059437373|.4851468131|.4893138665|
|plain200|.6205573460|.6598473195|.6477449212|
|plain400|.3183248559|.7196768813|.7104626168|
|standard200|.5485668558|.6139164436|.6044741007|
|standard400|.2572832050|.6487715053|.6412566982|

独自stdlib算術で全5901行のID/許可train-valラベル/side/STM f32距離/固定mask/group/phase/cohortを照合した。train-only入力分位binsも別算術で再算。Dはf32演算順を独自導出して全行一致、既199係数SHAと束縛した（係数fit全体の再監査はしない）。同一group内の元重み1/(G*n_game)で全モデルのrootmean/z MSE、符号、飽和、全game別指標を再算し保存parity集計と1e-12以内で一致した。保存旧曲線との差はownerの有限receiptにより最大約1e-10、checkpoint/source SHAは照合したが新forward再認証はしていない。

e=y−D、r=N−Dの恒等式gap=E[r²]−2E[e*r]を全体・排他的binsに適用した。standard400はtrainで.1265977633−.2752582957=−.1486605324、validationで.1929342920−.0293095998=+.1636246922。train残差整合の相関.6073に対しvalidation .0479。validation mean-bias寄与は.0001598475で、全体gapは主に振幅と弱い整合の差として記述できる。因果的なoptimizer/情報/教師ノイズ判定ではない。standard200もvalidation .1314079674−.0026383369=+.1287696305で、両stepで24game中9game改善・15game悪化。

全7分類で元重みmass合計1・signed gap合計が全体へ1e-12以内で閉じた。standard400 validationのearlyはmass .4410/gap+.09406265、middle .5590/gap+.06956204、lateは0行/0game/0mass（未知、改善0とはしない）。距離差5binすべて正gapで、特定一群だけの問題に局限しない。D飽和6行/2gameのmass .00355/gap+.00016089は小さく、非飽和1242行のgap+.16346380を隠さない。群内部平均を全体寄与へ読み替えず、群は事前label-free定義の探索的記述である。

**保存fieldの差**：元216 `walls_total` は設置数でなく、selfremaining+opponentremainingの合計。最初のopening8 witnessは残量9+8=17、設置3。元`walls_bin`はremaining stock binsとして全行再算・元版保持し、設置複雑性と解釈しない。独立結果にはplaced=20−remainingの別派生binsも保存した。全体MSE/予測/恒等式は不変。最初のchecker失敗版・差を保存し、同じ算術60秒枠で意味を区別して修復した。原科学negativeや新forwardへ変換しない。統括は最小ラベル修正を採用し216へ配送済み。

次の最大1方向は、統括のphase2 **learned standard400 hidden32を固定し、train-only標準化・gameweighted ridge λ.01/33係数でeを読出し、clamp(D+head)** を支持する。400stepのtrain適合はあるため、追加width/LR/teacherやfresh testを先行するより、既表現の読出しと距離アンカーによる汎化増分を低費用で判別できる。旧204は未学習特徴head、今回は学習済み表現＋固定距離＋ridgeであり異なる。重要留保は、距離アンカーと読出し法を同時に変えるため、有益でも元headだけの因果障害や表現転移を一意に確定できない点。trainのみ改善ならこの組合せの残差転移不足を残す。λ/零分散/非penalty intercept/非clip fitとclip評価は契約の結果前固定を支持する。phase2結果は本217 phase1独立認証の範囲外。承認gate・追加算術・旧test救済は求めない。

216 phase1追加forwardは23604samples、guardian elapsed1.51554449s、peak family RSS613748736B、exit0/wait/停止receipt。内部forward elapsed .18780385sは内包なので合算しない。元静的分析・pack費の確定総額は未確認。管理source-save syntax failure（実script未起動）とzero-row群表示修復v2/元v1を保存参照し、NN不一致・棋力敗北へ変換しない。

217は新NN/model/forward/train/test/GPU/build/import0。独立算術成功.51036s/peakRSS75567104B、CPU0単1。源読取60＋失敗修復込み算術60=保守的charge120/180、未使用60・旧214120/212120/210180は不変。正frame16 live monitor ownedNone・次quiet526s・216 exactPID/tick不在・物理heavy不在を直前admitした点証拠であり、将来や全hostの不在保証ではない。旧114930148B無減額＋新1MiB=115978724B<critic112MiB guard117440512B。自域保存/Git/一時/残metadataは実測forecastを別記する。

shared変換はoracleにimportせず独自算術にしたが、元opaquehistory/RuleA合法性/教師truthは追加認証していない。rootmean蒸留と真z診断を分け、再用validation・同一seed/入力・多群探索・同じtrainで学習したhiddenの限界を保持する。旧testlabels/results/raw/journal/mixedstatus/preview/173正式holdoutは未読、label-free containerのtest行は解析join前に除外した。棋力・独立test効果・NNUE全方式の成否は認定しない。

根拠：`research-data/ai-sigma/frame16-fit-gap-independent/{check.py,result.json,per-game.json.gz,calc-attempt1.json,check-attempt1.py,calc-admission*.json,science-stop.json}`。再現はCPU0の許可済quiet窓で `timeout 60s taskset -c 0 python3 -B research-data/ai-sigma/frame16-fit-gap-independent/check.py`（実行権限・残費は別確認）。原データ/源SHAはresult.json、元216結果/停止は参照のみ。

## phase2：残60秒の追加有限裁定（phase1を保持）

frozen standard400 hidden32のtrain-only ridge λ.01と、同sの2係数距離残差ridgeを独立NN0検算した。**この固定hidden読出しはtrain適合を増やすが、再用validationで距離基準を超えない**。元standard400に対する部分改善を、距離超過・独立test効果・NNUE情報不足の一意原因へ変換しない。

|方式|train gameMSE|validation gameMSE|validation rowMSE|validation 真z gameMSE|
|---|---:|---:|---:|---:|
|距離D|.4059437373|.4851468131|.4893138665|.8225350323|
|standard400|.2572832050|.6487715053|.6412566982|1.0032958247|
|learned-hidden ridge|.2085936615|.6127986850|.6101873693|.9783400132|
|距離2係数再調整|.3962950788|.4845397580|.4903769618|.8247985386|

hidden ridgeのvalidation差は対standard400 −.0359728203、対D +.1276518718、対距離再調整 +.1282589270。D比11/24game改善・13悪化。振幅.1483835006−整合減益.0207316288=gap+.1276518718が元gameweightで閉じた。early寄与+.0914436351、middle+.0362082367、late0行/0mass。距離再調整は対D gameMSE−.0006070551/15game改善だがrowMSEは+.0010630953、真zMSEは+.0022635062で符号増分0。微小game平均の改善を全面利益としない。

NPZをZIP/NPYヘッダ・f32 rawstorageとして解析し、5901rowIDs/32列・旧phase1行/labels/予測の一致を照合した。Torch/NumPy/model import・forwardは0。train96の元rowweightでpopulation momentsを再算しf32適用値一致、zero列[3]を確認。独自partial-pivot Gaussian solveで33係数・非penalty intercept・λ.01を再算、正規方程式残差1.11e-16、保存係数との差5.72e-14。scalar s参照もtrain-only moments/2係数を再算した。f32演算のdot積順序差を許容しhidden予測maxabs2.384e-7、距離参照0（新NN認証ではなく保存配列からの算術）。unclipped fitとclip評価を分け、hidden ridge train unclipped MSE .2308200120 vs clipped .2085936615、validation .6306019483 vs .6127986850を保存した。源の`measurements.saturation_fraction`は|prediction|>=.9、本独立結果の`saturation_*`は|prediction|>=1の厳密clip到達率であり別分母・定義。validation hidden ridgeの厳密到達130/1248=.10417、ownerの.9閾値.14984と混ぜない。

hiddenの実由来は固定source/pre-hook/同passprediction receipt/immutableモデルSHAに束縛した有限支持であり、現model forward・全教師truthの再認証はしていない。phase2 preregistration/初期版とscalar追加v2を区別する。scalar参照登録06:31:31はmain hidden job終了06:30:53の後、ownerは主metrics非閲覧と記録する。独立に証明できるのは版/hash/時間の対応までで、全人物理非閲覧保証ではない。referenceは新NN0、主要条件・旧成功数値不変。条件の追記時点を「main実測前」と捏造しない。

主配分は、追加学習を広げず読出しだけで汎化gapを縮められるかを実際に判別した点で有用だった。しかしhidden ridgeを既定候補へ昇格する根拠は不足。最大1の次方向は**次の許可単位でstandard200 hiddenを固定し、同D・同train-only λ.01 ridge・同scalar参照の一対照**。feature学習時期のみを変え、400の適合でhidden側へ残った汎化不足か、この単純読出しで解消できない差かを狭める。追加λ/width/LR/teacher/fresh testを自動先行しない。現在216の29505/30000余裕へ5901を無断追加せず、新配分の採否・費用判断に返す。改善しても時期と表現変化の有限比較であり教師noise/history/分布・表現全方式の一原因断定は残る。

216 phase2 actual5901/total29505<=30000、exit0/wait/currentidentity不在、全heavy4.815047723s（phase1+phase2）、peak familyRSS640339968Bの停止receiptと束縛した。217直前06:37:50に正frame16 monitor ownedNone、次quiet935s、producerPID4083106/tick34842201不在、heavy0、自controller PID/tick/RSS11.2MiB、forecast651264<716800をadmitした点証拠。独立job .48492s/peakRSS70881280B、自己PID4088531/tick34884290を保存。残source読取を含む60秒を元120に加算し**217 total180/180、残0**。旧charge/phase1 source-resultは変更0、追加NN/test/forward0。これ以降は必要保存・復元・backup・handoffのみ。phase2根拠は自域`check-phase2.py,phase2-result.json,phase2-per-game.json.gz,phase2-admission.json,phase2-science-stop.json`。
