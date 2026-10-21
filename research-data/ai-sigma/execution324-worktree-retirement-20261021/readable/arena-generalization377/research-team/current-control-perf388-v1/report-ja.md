# 現在のControl：保存profile388

現在のControlでは、解決できたself samplesの最大群は **sorting 157/565（27.79%）** だった。次の小候補は、現在の順位・signed history score・ActionID tieを一つの整数キーとして合法手ごとに一度作り、Controlの比較器の繰返し処理を減らすこと。これは提案のみで、費用削減量やwhole改善は未測定。maps検証を削除する提案ではない。

元の18探索はすべてCOMPLETE、9 reset sessions、UNKNOWN/Err/extraは0。3passesの6局面すべてで完成深さ、valuebits、action、exactPV、ALL recorded work、合法集合、fullhistory root、parent復元、stopが一致した。各passは真正387 image `ced70ad8`、Build `f4482c31`、built code `ada27a0`。読み直したのは保存metadataと今回のRAWだけで、探索・model forward・Perf-record・旧RAW decode・新candidate実装は0。

機械結果は [saved-interpretation.json](saved-interpretation.json)、大きいsymbol/callchain表は [profile.json](collection-v1/profile.json)、全時計・settings・workの元参照は [consumer.json](collection-v1/consumer.json)、6局面の完全一致確認は [comparison.json](collection-v1/comparison.json)。発行済みjob/config/settings/sequence/3 manifestsとRoot STOPのFileRefsは [selected-inputs.json](selected-inputs.json) にある。別の証明・認定・adoption ledgerは作っていない。

## 時計と母集団

| pass | whole before result publication秒 | setup秒 | target drop秒 |
| --- | ---: | ---: | ---: |
| plain-before | 11.583107747 | 0.018860473 | 0.000009939 |
| sampled | 11.667982548 | 0.018567331 | 0.000010465 |
| plain-after | 11.625947852 | 0.024043008 | 0.000009375 |

plain二観測のwhole中央値は11.6045277995秒。sampled/その中央値は1.005468（記述的には+0.547%）。別々の時点の有限三観測なので、純粋なprofiler overheadの因果推定ではない。session reset/teardown・root preparation/Search/journal等は保存時計に分離されているが、wholeに内包される時計を加算していない。記録nodesは全18calls合計21,148,161、evaluationsは15,520,353。

| 局面 | plain-before root秒 | sampled root秒 | plain-after root秒 | sampled/plain中央値 |
| --- | ---: | ---: | ---: | ---: |
| cold D4 family102 | 0.082917559 | 0.101146547 | 0.103117184 | 1.087394 |
| cold D6 family34 | 11.020268783 | 11.057222397 | 10.992040188 | 1.004640 |
| warm family0 local0 | 0.102075043 | 0.101802590 | 0.101949810 | 0.997943 |
| warm family0 local2 | 0.112005598 | 0.108167809 | 0.104059162 | 1.001254 |
| warm family0 local4 | 0.092068967 | 0.091953304 | 0.104265775 | 0.936699 |
| warm family0 local6 | 0.092045249 | 0.106057861 | 0.097853891 | 1.116991 |

root秒は `root_body_including_journal_seconds`。warmは元のroot indices4/5/6/7、local0→2→4→6の同じfresh warm session内の順序を保持している。sampled passのroot時間合計の95.598%はcold D6。samplesをroot別に分割したわけではないため、全局面に同じhotspot比率を当てはめない。

## 解決できたsamples

今回の唯一RAWは4,790,616B、SHA `a9e2ee3b7ebae13b80dfb805e0c92aabddc914e8de5559312dbe2abe14c800fa`。decode前後のhash/bytes/modeは一致。actual settingsは49Hz `cpu-clock:u`、DWARF8192、ring64、12582912B、no-buildid-cache。新たなeventは記録していない。

分母は565 samples、period合計11,530,612,095。self reportとscriptのperiod合計が一致し、reportのlostは0。自己費用はleaf symbolに解決したperiod、inclusive列はその群がcallchain内のどこかに現れるsampleのunionであり、群内でも同じsampleは一度だけ数える。**群同士は重なるためinclusiveを足さない。** 以下は一般CPU比率や原因別の確定time shareではない。

| 既存symbol群 | self samples / % | any-frame samples / % |
| --- | ---: | ---: |
| sorting / unstable / comparator内包 | 157 / 27.788 | 160 / 28.319 |
| `Search::ordered` | 62 / 10.973 | 227 / 40.177 |
| wall-distance map生成 | 59 / 10.442 | 63 / 11.150 |
| NNUE delta | 37 / 6.549 | 117 / 20.708 |
| NNUE feature/accumulator validation | 15 / 2.655 | 15 / 2.655 |
| NNUE head | 70 / 12.389 | 89 / 15.752 |
| legal generation | 66 / 11.681 | 67 / 11.858 |
| TT table | 3 / 0.531 | 3 / 0.531 |
| board hash | 4 / 0.708 | 6 / 1.062 |
| context fingerprint | 5 / 0.885 | 5 / 0.885 |
| repetition/history context | 9 / 1.593 | 9 / 1.593 |
| make/unmake | 5 / 0.885 | 21 / 3.717 |

最大の単独leafは `small_sort_network` 84 samples（14.87%）。quicksort42、insertion sort26等にも同じ `Ranking::sort` の比較closureが解決される。`ordered` leaf62は全て次祖先がunknownであり、score作成・初期配列・比較器等のinlined内訳を分離できない。map生成leaf59は記録callchain上で `wall_distance_maps → delta_move_into → advance_move_context → Search::child` に接続しているが、cache miss回数・不要BFS割合・387が省いた回数はUNKNOWN。

独立した `validate_maps`、cheap prepare、continuation scoring、FT-ID copyの解決symbolがないことは費用0を意味しない。ただし現Controlの `StaticScratch::CheapControl` は実際のsourceでは `goals_only` を呼び、Cheapの `prepare/validate_maps` とは別の経路。376の停止済みvalidate_maps案を現在のControl hotspotに読み替えない。NNUE feature/accumulator validationは別群で実際に解決される。

unresolved leafは33/565（5.841%）。全565 callchainsにunknown祖先と末尾sentinelがあり、frame数は2〜11。inlineの個別費用・完全なunwind・失われた祖先はUNKNOWN。`[unknown]`のinclusive100%は終端sentinelの観測であり、未知処理が全費用を占めるという意味ではない。lost0でもstack完全性を保証しない。software sampling一回・有限565点の順位を原因や将来benefitへ変換しない。

## 元の384 Controlとの記述比較

旧RAWを再decodeせず、元の保存384結果だけを参照した。384 Controlはimage `1b631ac7` / code `61a2fea`、今は`ced70ad8` / `ada27a0`。元のsampling時刻窓は82288.851607〜82300.503259、今回は93708.188984〜93719.730777（同じbootのperf時計）。比較する有限観測の時点・image/codeが異なる。

| 群 | 384 self % | 388 self % | 384 any-frame % | 388 any-frame % |
| --- | ---: | ---: | ---: | ---: |
| sorting | 30.473 | 27.788 | 31.173 | 28.319 |
| ordered | 9.982 | 10.973 | 53.765 | 40.177 |
| maps | 10.683 | 10.442 | 11.384 | 11.150 |
| delta | 5.254 | 6.549 | 21.016 | 20.708 |
| head | 11.033 | 12.389 | 13.135 | 15.752 |
| legalgen | 9.807 | 11.681 | 9.982 | 11.858 |

384は571 samples / period11,653,061,073、今回は565 / 11,530,612,095。plain wholeは旧11.940464615・11.894066602秒、現11.583107747・11.625947852秒。ただし386で5rootのworkが変わっており、比較時点も異なる。割合変化・whole差をsame-work speedや387 cache再用だけの効果とは呼ばない。元384 FAILED/UNKNOWN/fees、386のexact-order-work FAIL、376採用FAILをこのprofile結果で変更しない。

## 最小の次候補

第一候補は `move_ordering.rs::Ranking::{new,sort,compare}` と `alphabeta.rs::ordered` の **Control・policyなし・signed score** に限定した一度の整数sort-key作成。現在のsourceは合法手ごとのPV/goal/killer rankを既に保存するが、sort比較ごとにrank、history降順、ActionID tieの段階比較を行う。この意味をそのまま表すkeyを保存し、比較器を一つの整数比較へ縮める。優先段階・signed scoreの全境界・最後のActionIDが同じなら全順序は同じで、scoresや探索順序を変更する必要はない。policy Someの`total_cmp`（±0を含む）とunsigned診断経路は対象外として保持する。

必要費用はper-ID key作成の処理と保存領域。独立した209個のu64なら約1,672Bの固定stack、既存rank領域へ最小構成できるかは実装時の問題。heapを増やす理由はなく、初期store/cache footprintによって比較削減が相殺される可能性もある。isolated comparator費用・benefitは今回のsamplesからは分からない。選択された場合だけ、rank hierarchy・signed extremes・ties・policy ±0/exclusion・診断ON/OFF・既存cancel/error/parent境界を意味のある小softwareで確認し、Rootが別途選択した有限評価を行う。**本leafでは実装・build・追加計測を行っていない。**

第二の観測としてmap生成はなお59 samplesだが、387はmatching parent優先とpooled child-map fallbackを既に採用している。どの実transitionがmissしたか未記録なので、そこから新cacheや検証省略を作らない。FT-ID copyも独立に解決せず、source上のcopy可能性だけから費用や省略の利益を確定しない。

## 実行・保存範囲

`perf report` self/inclusiveと`perf script --show-lost-events`の三つだけを既存CycleResources/executeで実行した。worker CPU3、512MiB family、host reserve4GiB、GPU0、no_new_privs要求/exec前1確認、full bounded capture、directwait/reap/handles close、remaining[]。returned settled masksと元のpersisted pending/attemptedは別々に機械結果へ保存している。decode用TMPは消失、元のRAW/image/sourceは書いていない。元のnative/profiler/guardian/outer STOPはRootの記録を参照し、profilerのnativeをguardian直接waitしたという保証は追加していない。

限定Ruff format/lintはPASS。解析sourceとdecoder readerはSTOP、追加Search/model/Perf-recordは0。実childのfresh不在/別identity、directreap、TMP、owned[]は最終STOPに記録する。OWNの一度のpost-work usageは最終receiptへ記録し、共有assets/image/target/Beads、元のRAWやグローバル実容量を今回の新増加として数えない。leafはRootのscope受入れ後にcloseする。
