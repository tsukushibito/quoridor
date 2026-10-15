# 416：LMRの限定観測・最小実装仕様

設計のみ。新Search・対局・model load・solver・fit・bootstrapは実行していない。目的は次の二仮説の局所的な成立例と反例を得ること。製品既定・LMR式・methodを変更しない。

1. **H0保護**：浅い上位の適用可能手にq=0を与えることで、extra=1ならalpha以下へ落ちる候補を残しているか。利益が無く通常深さの仕事だけ増える可能性も調べる。
2. **H+見落とし**：正qの浅いfail-lowに、通常深さならalphaを超える候補が残るか。冷状態でも浅いfail-lowが再現するかを先に区別する。

旧392局の勝敗・CIは再審査しない。根拠は `research-data/ai-sigma/lmr-game-analysis415/report-ja.md` と `examples.json`、現 `crates/quoridor-ai/src/alphabeta.rs` の `lmr_allowed/reduced_child/child`。q=0は通常PVS、正qは浅いscoutがalphaを超えた場合だけ通常深さ確認、必要時に通常PVS full-windowへ進む実装である。

## 収集と独立照合

固定12例を元のevaluatorのまま使う（NNUE勝1,2,5／負8,12,20、固定D勝1,5,7／負3,20,21）。同じ新image・model・score domain、Control/PVS/TT1M、depth_rank、approx/exactleaf OFF。各rootは新sessionの空TT・初期history/killer、元の完全な対局履歴から開始し、反復深化max_depth=5、max_nodes=1,000,000、time_limit=Noneで1回。100ms対局の再現・性能測定ではない。cancel/errorは既存手順で停止し、打切り分を補充しない。

各rootで最大4枝だけ保持する。H0は eligible=true、q=0、distinct-hand rank=4..8について、内部親depth=3と4で各最初の1枝を**返値を見る前に**予約。H+はeligible、q>0、内部親depth=3..4、浅いscoutが完了してshallow<=alphaとなった枝からq=1とq>=2で各最初の1枝。反復順・DFS順を固定し、同じ親履歴+actionの重複は各仮説内で除く。該当無し・予約枝の中断は欠測、別枝へ交換しない。固定サイズのdepth/rank/q集計で適用機会・完了・fail-low・確認数を残し、枝全体のtraceや全合法手scoreは保存しない。

元Searchが終了してから、保存枝を二つの**相互独立な新session**で照合する。親の盤面・完全repetition履歴・元rootからのPlayedMove path・元の非root plyを戻し、既存内部 `child`/scoutを直接使う。子を新しいroot探索へ昇格させず、反復深化も挿まない。TTは各照合ごと空1M、history/killerは初期状態。評価器・下位LMR・ordering等は二本で同じ。元のTT/history snapshotは作らず、元Searchや別probeへの書戻しも行わない。

親depthをdとすると、H0の仮想reducedは **d-2（extra=1）**、normalはd-1。H+のreducedはd-1-q、normalはd-1。二本とも元の**post-TT / pre-child alpha**で親視点 `[alpha,next_up(alpha)]` を渡し、内部の符号反転は共通childに任せる。各呼出しmax_nodes=100,000、time_limit=None。独立した単発scout二本であり、fail-high時の自動確認やfull-window再探索は追加しない。子孫では現行depth_rankを維持するためnormalも選択的推定である。

最大12 root Search + 48枝×2内部scout = **108呼出し、21,600,000 search nodes**。node capは共通enter/controlが数えるnodesで全子孫を含む。欠測・cap・cancel・errorはUNKNOWN、再実行・補充・拡張なし。H+の採取条件自体がcapで未確定なら採らない。NNUE family5の元fallbackはその事実を残し、この新診断が成功しても旧原因を解決したとしない。

## Sol/highへ渡すfield

| field群 | 意味・上限 |
| --- | --- |
| run/root | image/build、evaluator/model/domain、source refs、例ID/元game/ply、root完全履歴ref、session初期化条件、limits、最終stop/完成深さ、累積nodes/evals。既存measurement出力を再用 |
| branch key | iteration_depth、訪問連番、親までのaction/colour path、非root ply、parent state/fullhistory照合値、action。parent履歴はroot履歴+pathで復元しcountsを検査。hash単独を復元入力にしない |
| gate/order | parent depth、distinct-hand 1始まりrank、eligible、q、実child depth、選択bucket。TT合法手/利用深さ/bound/context-match、既存保護フラグを既に算出済みの値から保存。history/killer全表は保存しない |
| windows/returns | 親STM視点、post-TT alphaとbeta、実scout窓、各段階shallow/通常深さ確認/full-windowの有無・value f32 bits・完了/中断。alpha更新前に固定し、段階の無い値はnull |
| isolated probes | cold条件、指定/実深さ、同窓bits、返値bits、Upper/Lower/Exact-or-UNKNOWNの根拠、nodes/evals、stop/completed、元観測との一致/不一致。履歴/窓/視点の不一致は比較無効 |
| coverage | H0のdepth3/4、H+のq1/q2以上別に機会・保持・欠測。小さい固定bucketのみ。診断bufferは最大4枝/root、48枝全体 |

scoutが完了してv<=alphaならUpper、v>=next_up(alpha)ならLowerと扱う。幅1 ULPなので通常は内点Exactを得ない。TTから来た既存boundも保存し、returned値を真値へ昇格させない。元parentのbetaやTTによる狭窓と照合窓は混同しない。capで返った前回完成snapshotを指定枝の完了値へ流用しない。

## 判定と実装境界

H0でcold reduced<=alphaかつcold normal>alphaなら、q=0保護が局所的に有望な手を残す例。H+は元shallow<=alphaに加えcold reduced<=alpha/cold normal>alphaなら冷条件で再現する見落とし候補。cold reduced>alphaなら元warm経路から移した時点で条件が変わり、局所的な削減損失を同定できない。両方fail-low・両方fail-high・UNKNOWNも分母付きで残す。二本のnodes/evalsは局所費であり、実際のconfirm時のTT再利用費やroot総速度の推定に足し合わせない。

結果選択されたprefix4の12例と先頭枝に偏る。旧warm TT/history・先行探索・時計は再現しない。候補頻度の母集団推定、旧勝敗の原因、q=0全体の利益、ゲームWDL/棋力優越は分からない。改善案の採否ではなく次の仮説更新まで。

既存research-diagnosticsとmeasurement入口へ小さい限定sink/終了後probeを加え、共通child/undo/controlを再用する。非診断buildはcfgで記録処理を消し、feature有効でもOFFでは追加のlegal生成・score計算・allocation・ログ・counter walkを行わない。動的分岐も増やさない必要があれば既存診断経路内へ置く。一般replay framework、TT snapshot、registryを新設しない。

実装側の限定検証は、OFFとONの固定node/depthでaction/valuebits/既存stats一致、q0とpositive-qのdepth/window/sign、TT保護・root非適用、cap/undo/元session非変更、完全history/path復元。実装担当の既存fixtureと関連testへ限定し、ここではcompile/Searchしていない。通常コード整形とMain/Git/Cargo所有は324のまま。
