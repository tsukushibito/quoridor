# 複合key採用後のControl：保存Perf390

今回解決したsorting群はself **68/485 samples（14.02%）**。内訳はquicksort52、insertion13、pivot3で、整数比較だけの費用ではなく、比較closure・partition・移動・制御を内包するsort関数の観測である。`Search::ordered` self66（13.61%）、map生成70（14.43%）も残るが、key作成を独立に分離したsymbolはない。新たな最適化・instrumentation・sampling・buildは発行していない。

元の18探索・9sessionsは全COMPLETE。3passesの6局面すべてでdepth/valuebits/action/exactPV/全30記録work/合法集合/fullhistory root/parent復元/stopが一致した。imageは全て`09149bda`（8,740,032B）、Build `a2ae2162`、code `177b006`、boot `6c2e177d`。BEST43・TT4096/PVS・cold D4 family102/D6 family34・warm family0 local0→2→4→6の設定は元の発行済み記録を保持した。UNKNOWN/Err/extraは0、全18call合計nodes21,148,161/evaluations15,520,353。

機械結果は [saved-interpretation.json](saved-interpretation.json)。大きいsymbol/callchain表は [profile.json](collection-v1/profile.json)、元のsettings/時計/workを参照する [consumer.json](collection-v1/consumer.json)、全6局面の一致は [comparison.json](collection-v1/comparison.json)。実際のsettings・job config・sequence・3 manifests・唯一RAW・Root STOPのFileRefsは [selected-inputs.json](selected-inputs.json)。新しい認定・measurement frameworkは作っていない。

## 全体時計と局面

| pass | whole before publication秒 | setup秒 | target drop秒 |
| --- | ---: | ---: | ---: |
| plain-before | 9.920899369 | 0.019302551 | 0.000009200 |
| sampled | 9.961989159 | 0.022062484 | 0.000009743 |
| plain-after | 10.059865943 | 0.054737242 | 0.000009023 |

plain二観測のwhole中央値は9.990382656秒、sampled/plain中央値は0.997157917（記述上−0.284%）。sampledが近傍plainより短くなることもあり、これをprofilerが高速化する証拠や純粋なoverhead推定とは扱わない。setup/drop/reset/teardown/準備/Search/journalの時計は元記録に分離されるが、wholeへ内包されたnested時計を足さない。

| root | plain-before秒 | sampled秒 | plain-after秒 | sampled/plain中央値 |
| --- | ---: | ---: | ---: | ---: |
| cold D4 family102 | 0.072466548 | 0.079994921 | 0.072692398 | 1.102170 |
| cold D6 family34 | 9.417663632 | 9.466220600 | 9.513545359 | 1.000065 |
| warm local0 | 0.087938651 | 0.089897258 | 0.093691127 | 0.989896 |
| warm local2 | 0.105837186 | 0.088011509 | 0.089918118 | 0.899199 |
| warm local4 | 0.077904478 | 0.079992719 | 0.091984480 | 0.941706 |
| warm local6 | 0.083957874 | 0.075952169 | 0.077859239 | 0.938741 |

root秒は `root_body_including_journal_seconds`。warmの元root indicesは4/5/6/7で、同じfresh sessionのchronological順。sampled passのroot時間の **95.811%がcold D6**。ただしsampleはroot別に分割していないため、95.811%をD6のsample比率と呼ばず、hotspotがcold/warm全局面に共通とは推論しない。

## RAW・分母・sort内部

唯一RAWは4,115,320B0600、SHA `392610f1b59c818cbc50c0663f619220fb757f3c640517a172fed4b03c08a089`。既存388 entryのdecode前後のstreamed hash/bytes/modeチェックが一致した。49Hz `cpu-clock:u` / DWARF8192 / ring64 /12582912B/no-buildid-cacheの実設定をそのまま保存している。新eventをrecordせず、今回RAWだけを標準self/inclusive reportとscript lost表示でdecodeした。

分母は485 samples、period合計9,897,959,055。self reportとscriptのperiodが一致し、report lostは0。selfは解決したleafのperiod、inclusive群は群内のいずれかのframeが現れるsampleのunion。同じsampleを群内で重複計上しないが、**異なる群は重なるので加算しない。**

| sorting内の実symbol | self samples / % | そのsymbolのinclusive % |
| --- | ---: | ---: |
| `unstable::quicksort::quicksort` | 52 / 10.722 | 14.02（report丸め） |
| `smallsort::insertion_sort_shift_left` | 13 / 2.680 | 2.68 |
| `pivot::median3_rec` | 3 / 0.619 | 0.62 |

三者は`Ranking::sort_control`のkey比較closureを含むinstantiationに解決した。self leafは別々の観測だが、inclusiveではquicksortの子にinsertion/pivotが入るので、14.02+2.68+0.62を足さない。sorting群のany-frame unionも68/485（14.021%）。partitionだけ・exchangeだけ・整数compareだけ・move/copyだけの独立費用は分離できない。`small_sort_network`やmergeの独立symbol/sampleも今回は解決せず、費用0やその処理の不在を証明しない。

## whole-searchの解決群

| 群 | self samples / % | any-frame union samples / % |
| --- | ---: | ---: |
| sorting | 68 / 14.021 | 68 / 14.021 |
| ordered | 66 / 13.608 | 152 / 31.340 |
| maps生成 | 70 / 14.433 | 71 / 14.639 |
| NNUE delta | 34 / 7.010 | 138 / 28.454 |
| feature/accumulator validation | 23 / 4.742 | 23 / 4.742 |
| NNUE head | 54 / 11.134 | 72 / 14.845 |
| legal generation | 41 / 8.454 | 43 / 8.866 |
| TT table | 2 / 0.412 | 2 / 0.412 |
| board hash | 2 / 0.412 | 2 / 0.412 |
| context fingerprint | 8 / 1.649 | 8 / 1.649 |
| repetition/history context | 15 / 3.093 | 15 / 3.093 |
| make/unmake | 7 / 1.443 | 37 / 7.629 |

`ordered` leaf66の次frameはunknown。score/history/rank/key準備がinline化されていても、66全てをkey準備と呼べない。独立したcontinuation scoring、FT-ID copy、cheap prepare/map validationはUNKNOWN。Controlの既存goals-onlyとCheap prepareの別subjectを混ぜない。map leaf70は保存callchainで `wall_distance_maps→delta_move_into→advance_move_context→Search::child`、legal leafは `legal_action_ids→SigmaContext::legal_ids→child`、headは `evaluate_with_scratch→child`に接続している。ただしdynamic calls、cache-hit、skip-BFS、copy回数・重複BFS率は未記録ならUNKNOWN。

unresolved leafは41/485（8.454%）。全485 chainsにunknown祖先/末尾sentinelがあり、frame数は2〜11。lost0でもunwind完全性はUNKNOWN。inline責務別の費用、symbolが出ない処理の費用、未知ancestorの中身は分からない。whole有限49Hz一回の順位は一般CPU割合・原因別確定費用・強さの証拠ではない。

## 元の388との保存summary比較

旧RAWを再decodeせず、同じOWNの旧388 saved summariesだけを参照した。旧388はimage `ced70ad8`/code `ada27a0`/boot `2c53965e`、今390は`09149bda`/`177b006`/boot `6c2e177d`。旧sample窓93708.188984〜93719.730777、今4466.706405〜4476.599173は **異なるbootのperf時計**なので、時計値を連続時刻や直接経過差として引き算しない。実study時刻も旧03:08STOPと現05:26STOPの別観測である。

| 群 | 388 self samples / % | 390 self samples / % | 388→390 any-frame % |
| --- | ---: | ---: | ---: |
| sorting | 157 / 27.788 | 68 / 14.021 | 28.319→14.021 |
| ordered | 62 / 10.973 | 66 / 13.608 | 40.177→31.340 |
| maps | 59 / 10.442 | 70 / 14.433 | 11.150→14.639 |
| delta | 37 / 6.549 | 34 / 7.010 | 20.708→28.454 |
| validation | 15 / 2.655 | 23 / 4.742 | 2.655→4.742 |
| head | 70 / 12.389 | 54 / 11.134 | 15.752→14.845 |
| legalgen | 66 / 11.681 | 41 / 8.454 | 11.858→8.866 |

旧565 samples/period11,530,612,095と現485/9,897,959,055で分母も異なる。旧のsort内部はsmall_sort_network84、quicksort42、insertion26等が解決したが、今回はquicksort52/insertion13/pivot3。同一アルゴリズムの全動的呼出し数やper-element比較回数を測った値ではない。

保存summaryでは旧388と現390の全6rootのdepth/valuebits/action/exactPV/ALL記録work/合法集合/fullhistory/parent/stopも一致した。旧plain whole中央値11.6045277995秒、現9.990382656秒。ただしimage/code/boot/時間・環境・有限samplesが異なる別の観測であり、割合差を複合keyだけのisolated causal benefitや普遍速度へ変換しない。389の既承認O-N-N-O24 finite比較は別の原記録のまま保持し、再実行・estimator変更・再採否はしない。

## 実行とshared-writer境界

既存388 decoderを同じsourceのまま、`--runs`/`--out`だけ390のOWNへ指定して再用した。CPU3・512MiB family・host reserve4GiB・GPU0、既存CycleResources/execute/fullcapture/no_new_privs（exec前1確認）で新RAWの三commandを一度実行。directwait/reap/handles、原childのfresh不在/別identity、TMP消失、remaining[]は保存receiptに結合した。returned settled masksと元disk pending/attemptedは別々で、ないguardian returnを作っていない。

actual decoder readerSTOPは05:29:51.430985Z。active canonical leaseはその操作の終了時に解放した。Rootのgeneration-v3は共有leaseのEAGAINでnative前に拒否したとの原記録を保持し、CPUが分離していてもwriter leaseが直列資源である点を明示する。[shared-writer-release-STOP.json](shared-writer-release-STOP.json) を一度送付後、canonical/Main reader取得を新たに行っていない。Rootのactual generation entry確認後のこの報告・表・機械結果は、凍結したOWN summariesだけで作成した。元のgeneration failures/costを成功扱いにせず、独立CPUだけからglobalquietも主張しない。

新たなsource/最適化/measurement framework、decoder再実行、Search/model forward、Perf-record、instrumentation、build/symbol downloadは0。Python入口は元388の整形済みsourceをそのまま再用、今回の日本語Markdownは既存表/段落様式で限定整形した。OWN実usageを最後に一度記録し、shared assets/image/model/target/RAWや旧evidenceを今回の新増加に数えない。actual processor/reader/TMP/lease STOPとowned[]を最終receiptで返す。leafはscope acceptanceまでin_progress。

Mixed data/trainingのAUTONOMOUS SELECTEDは現在の選択として保持し、昔の未回答waitへ戻していない。323USERPAUSE/fits96/models/defaults/seals、元RAW/FAILED/fees/UNKNOWNは不変。Rootへのscope reportのみで、Policy copyや新しい候補campaignは発行しない。
