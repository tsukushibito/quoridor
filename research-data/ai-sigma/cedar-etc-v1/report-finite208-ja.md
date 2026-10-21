# ETC31 固定208 callsの有限比較結果

今回の depth3_top2 は **RETAIN_OFF_NO_FINITE_SUPPORT**。条件付き256局は未発行のまま進めない。固定条件で必要なprobe込み時間改善・反復条件・実cutoffを満たさなかったという限定結論で、一般的な無効果・劣位・同等性・棋力・Eloの主張ではない。

新共通BUILD3c5d75b7/image1c68b12a、Cedar35cbb/Current/Control/既存LMR/PVS/path_tail/TT1M/N1、MPCとsampler absent・aspiration OFF。既定OFF対depth3_top2の一因子。元26 genuine fullprefixを6同色時系列セッションのまま各passで使用し、全先行rootを維持。D4 OFF-ON-ON-OFF、D64/100ms+5ms ON-OFF-OFF-ON、計208 calls/48 sessions、11,474,501 nodes。元8 normal manifest/dataはPASSで、追加Search・新入力・warmup・refill・RNG・CIは0。

| 操作 | 条件/arm | Search合計s | nodes | evals | CPU合計s | setup s | reset s | session drop s | driver whole s | peak RSS MiB | ETC probes/cuts |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | fixed_D4/OFF | 0.906884021 | 807461 | 546593 | 0.88 | 0.001516 | 0.207647 | 0.012807 | 1.257063 | 91.00 | OFF/未収集 |
| 1 | fixed_D4/ON | 0.896250482 | 807461 | 546593 | 0.89 | 0.001517 | 0.247250 | 0.019231 | 1.280847 | 91.15 | 69/0 |
| 2 | fixed_D4/ON | 0.917012452 | 807461 | 546593 | 0.93 | 0.001628 | 0.220209 | 0.016774 | 1.274957 | 91.24 | 69/0 |
| 3 | fixed_D4/OFF | 0.906423760 | 807461 | 546593 | 0.89 | 0.001563 | 0.179701 | 0.013836 | 1.230819 | 91.38 | OFF/未収集 |
| 4 | clock100ms5/ON | 2.485707455 | 1987026 | 1482316 | 2.45 | 0.001586 | 0.223276 | 0.016324 | 3.151286 | 91.27 | 17253/0 |
| 5 | clock100ms5/OFF | 2.493295771 | 2086216 | 1567914 | 2.50 | 0.001577 | 0.187335 | 0.019848 | 3.119375 | 91.04 | OFF/未収集 |
| 6 | clock100ms5/OFF | 2.495887838 | 2079919 | 1566407 | 2.51 | 0.002338 | 0.184839 | 0.014336 | 3.182300 | 91.02 | OFF/未収集 |
| 7 | clock100ms5/ON | 2.488010567 | 2091496 | 1574162 | 2.50 | 0.001610 | 0.222848 | 0.013716 | 3.085161 | 91.27 | 16845/0 |

Searchには追加make/probe/restoreとETC counterの費用を含む。setup/reset/drop/driver whole/通常job外側時間をSearchへ加算しない。CPUはOS process ticksで粗い。RSSは各process累積highwaterで、root毎の増分・常駐モデルの純サイズではない。raw nine-bin ETCカウンタ、TT/LMR/PVS等のwork、journal/stop-tail/target dropはper-condition.jsonとper-root-calls.json/CSVへ保存した。OFFのcounter object不在は観測0として捏造していない。

## 凍結ゲート

| 条件 | 実測 | 判定 |
| --- | --- | --- |
| D4全104 requested DepthComplete | True | PASS |
| pooled ON/OFF ≤0.98 | 0.9999752678500198 | FAIL |
| max(ON2反復) < min(OFF2反復) | ON [0.896250482, 0.917012452] / OFF [0.906884021, 0.90642376] | FAIL |
| stock合計比≤1.10、root両反復badcaseなし | stock=True, root=True | PASS |
| 全clock104 main receipt≤100ms/合法depth≥1/復元/error等なし | max 0.081854244s / late 0 | PASS |
| 全clock104 terminal Search p95linear≤110ms/max≤125ms | 0.1001357651s / 0.103307634s | PASS |
| 実機会と最初の通常子以後のqualifying cutoff | opportunitiesあり / cuts 0 | FAIL |

固定D4で26/26rootのaction/PV/valuebits/depth/stopは4条件すべて一致し、同armの2反復も26/26で出力・保存したworkが一致した。この観測範囲の一致であって、一般的なfullwidth同値証明ではない。各armとも各反復807,461 nodes/546,593 evalsで、ONは追加TT/key probesを持つため全内部workが同一という意味ではない。

stockは保存されたnative root_walls_remaining（両者のstock合計）を使用。0/1..4/5..10/11..20のroot数は2/6/6/12、固定比較の対応比は次表。入力payloadやgeometryから再計算していない。

| 両stock合計 | root数 | calls | pooled ON/OFF |
| --- | ---: | ---: | ---: |
| 0 | 2 | 8 | 1.008437572 |
| 1..4 | 6 | 24 | 0.892680149 |
| 5..10 | 6 | 24 | 1.056805862 |
| 11..20 | 12 | 48 | 0.998126276 |

root badcaseの凍結定義はmin(ON2反復)/max(OFF2反復)>1.20 **かつ** 正の超過>2ms。該当0/26。stockやrootの都合のよい部分集合へ選び直していない。

## 実機会と適用限界

D4 ON合計はopportunities 138、child probes 138、strict child TT qualified hits 0、terminal proofs 0、ETC cuts 0。100ms ON合計はそれぞれ23706/34098/0/2753/0。terminal proofはTT qualified hit/cutと別counterであり、2,753 terminal proofsをcutoffに置き換えない。実probe機会はあるが、今回の厳密depth/context/Bound契約で使えるTT hitとcutoffは観測されなかった。各拒否原因の頻度は今回のcounterではUNKNOWNで、深さ/contextを緩める理由や新candidateの許可ではない。

clock104件は100 TimeLimit +4 DepthComplete。requested D64のTimeLimit horizonはUNKNOWNのまま。合法にcommitした主結果と100ms receiptの資格は別で、全D64/同じ木を完了した速度ではない。4条件全出力一致は23/26root、両ON反復で両OFFよりdepthが2以上落ちるrootは0。LMR選択木、未完了の次iteration、clock変動が異なるため、action/PV/valueやnodes差をETCの棋力・因果効果・samework speedupとしない。6時系列/3元familyを共有し、26独立標本や棋力oracleではない。

## コスト・保存・次の扱い

元v2親command 129.559729733970sを一度だけ計上。accepted inclusive 131.326525sは代替domainで二重加算しない。旧12990ab9のFAILED command7.382441982044838s（accepted9.170955s代替）も履歴に保持し、内側native/子jobを追加計上しない。software/source/collector失敗・NULL・mask/persist・全fees/globalactual/later tails UNKNOWNは保持。

全8 native+normal collection/source STOPと最後の正常なfull17root保持730,714,112Bは先にRootへ配送した。これは一度の元normal観測で、分析/admin/delivery後のtailを含むglobal現在量や歴史的peakではない。再walk・quota refund/lendingはしていない。

固定208は使い切り。条件付き256局は不適格かつUNISSUEDで、追加call/別depth/probe数/soft-depth/context緩和/再対局/CIへ進めない。既定OFF、models/重み/product/generator設定は変更しない。Rootの有限解釈受入れと現行source境界に従い、不要な比較専用ETC API/counter/testの疎撤去を別途実体化し、共通現役機能・証拠・Git再構成元を保持する。現時点でauthor Main/Cargo/docs変更・review dispatch・自家source clearは0。

根拠: summary.json、per-condition.json、per-root-comparison.json、per-root-calls.csv、../collection-v1/collection.json。Rootの凍結7385d3a6 sidecarと元6d1679a9提案は不変。
