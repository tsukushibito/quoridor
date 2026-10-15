# 可変LMR三候補の有限比較と撤去（413）

現行A=depth_rankを研究標準として維持し、今回の追加候補B/C/Dは採用しない。192探索は全件NodeLimitでD8未完成、384対局は全件完了し、12対照の保存family単位95%区間はいずれも0.5を含むか接した。これは同等・劣位の証明でも候補同士の確定順位でもない。

具体的な追加用途・実験予定がない候補の現役enum/設定/追加専用counterとテストを通常保守として撤去した。原科学image b9d515e7/Build1af3ad9e、実設定、元RAW、失敗・費用・UNKNOWNは保持する。撤去commit b2ce8658は新Rust拒否2＋影響q0一件=3、Python拒否1、Clippy3、真正releaseをPASS。撤去後image7dadc2b3/Build ef7abadfは元比較に使っていない。共通A/FixedOne/OFF、412の標準、410/411の数学・履歴・TTを保持する。

元source・限定source確認と元有限結果の独立解釈は別々にclear。回収helper初回はtool version七件もコマンド数へ含めたためassertion失敗し、helperだけを訂正して元結果を回収した。nativeテスト/buildの再実行は0。元software E0308失敗、実行0件だったmetadata filterと後の真正初回一件、collector失敗、timestamp erratumも保存した。

元数値outerは探索費750.297630404秒＋対局1989.259172560秒、元softwareはFAILED込み111.815993823秒、撤去softwareは100.848559701秒を各一度。nestedを足さず、全source/LLM/admin費・連続family RSS・physical NN・孤立した削減演算費はUNKNOWN。全設定・結果・薄い源泉patch/復元gzip・費用・失敗・実STOPとレビューは[receipt](receipt.json)およびSHA-size-modeを往復確認したexact archiveに保存した。元fixed packetのretirement=PENDING記載は当時の履歴として凍結し、今回のreceiptで実際の撤去完了を区別する。

以下は変更しない元保存解析。公開作業による新Search/対局/solver/bootstrapは0。零在庫近似・安全先着leafは元比較でOFF、製品/実generatorのLMR enable OFFと全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更を保持する。

---

# 413：原384局と固定192探索費の保存解析

原384局は384 unique/entered/returned、192 complete colour pairs、383 goal・1 threefold draw、UNKNOWN0だった。候補をLEFT、基準AをRIGHTとして12対照を別々に保存した。全12の未補正family区間は50%を含むか端点で接しており、今回の有限探索的データから候補の一般優越・Elo・非劣性や確定順位を認定しない。候補の保持/撤去・Main変更はRoot判断で、本解析は追加候補/比較/ゲームを発行しない。

A=depth_rank、B=depth_rank_late_one、C=depth_rank_deep_two、D=depth_rank_early_one。NNUE BEST43/固定D(0,8,tanh)×Control/Cheapの4層に、各B/C/D対Aの3対照。各対照は同じ16 family×2色32局。旧412のLEFT=A/RIGHT=Bへ反転せず、nativeのLEFT候補得点と区間をそのまま引用した。

## 対Aの保存対局成績

| 層               | 候補 | 候補W/D/L/UNKNOWN | 候補得点 | 保存native 95%区間  |
| ---------------- | ---- | ----------------: | -------: | ------------------- |
| nnue/control     | B    |         14/0/18/0 | 0.437500 | [0.312500,0.562500] |
| nnue/control     | C    |         11/1/20/0 | 0.359375 | [0.218750,0.500000] |
| nnue/control     | D    |         15/0/17/0 | 0.468750 | [0.343750,0.593750] |
| nnue/cheap       | B    |         16/0/16/0 | 0.500000 | [0.375000,0.625000] |
| nnue/cheap       | C    |         14/0/18/0 | 0.437500 | [0.312500,0.562500] |
| nnue/cheap       | D    |         16/0/16/0 | 0.500000 | [0.375000,0.625000] |
| distance/control | B    |         19/0/13/0 | 0.593750 | [0.500000,0.687500] |
| distance/control | C    |         18/0/14/0 | 0.562500 | [0.406250,0.718750] |
| distance/control | D    |         17/0/15/0 | 0.531250 | [0.406250,0.656250] |
| distance/cheap   | B    |         14/0/18/0 | 0.437500 | [0.312500,0.562500] |
| distance/cheap   | C    |         19/0/13/0 | 0.593750 | [0.468750,0.718750] |
| distance/cheap   | D    |         17/0/15/0 | 0.531250 | [0.437500,0.625000] |

各区間の単位はcomplete family pair、元native 10,000 resamples/seed41320261015。新bootstrap0。固定book/config条件付きで、家族交換可能性・lineage依存未補正・多重対照/候補選択依存という限界がある。384独立標本でも、B/C/Dの直接対戦でもない。対Aの得点のみを用いた候補間の確定順位は作らない。旧408/412/400の結果を混合・再集計していない。

family順は14,16,23,27,37,38,39,44,64,74,82,86,103,109,118,124。全12×16 familyの二色個別score/平均/参照A平均、slot/run/batch/local game/色/圧縮journal行をresult.jsonへ保存した。1 drawはNNUE Control C対Aのthreefold_draw。maxply/forfeit/未回収/UNKNOWNは0で、上限やエラーをdrawへ変換していない。

## accepted completed snapshot depth

| 層/対照               | 側  | 完成n | 中央値 |      平均 | p95 | 最大 |
| --------------------- | --- | ----: | -----: | --------: | --: | ---: |
| nnue/control/B対A     | B   |   807 |      5 |  9.973978 |  24 |   64 |
| nnue/control/B対A     | A   |   809 |      5 | 10.592089 |  26 |   64 |
| nnue/control/C対A     | C   |   717 |      5 | 10.018131 |  27 |   64 |
| nnue/control/C対A     | A   |   722 |      5 |  9.738227 |  25 |   64 |
| nnue/control/D対A     | D   |   795 |      5 | 10.724528 |  28 |   64 |
| nnue/control/D対A     | A   |   796 |      5 | 10.537688 |  28 |   64 |
| nnue/cheap/B対A       | B   |   725 |      4 |  7.998621 |  21 |   64 |
| nnue/cheap/B対A       | A   |   725 |      4 |  7.852414 |  21 |   64 |
| nnue/cheap/C対A       | C   |   760 |      5 |  9.275000 |  25 |   64 |
| nnue/cheap/C対A       | A   |   762 |      5 |  9.217848 |  25 |   64 |
| nnue/cheap/D対A       | D   |   752 |      5 |  8.901596 |  23 |   64 |
| nnue/cheap/D対A       | A   |   752 |      5 |  8.550532 |  22 |   64 |
| distance/control/B対A | B   |   894 |     11 | 12.755034 |  26 |   64 |
| distance/control/B対A | A   |   891 |     10 | 12.796857 |  26 |   64 |
| distance/control/C対A | C   |   894 |     11 | 13.315436 |  29 |   64 |
| distance/control/C対A | A   |   892 |     11 | 12.909193 |  27 |   64 |
| distance/control/D対A | D   |   894 |     10 | 12.549217 |  30 |   64 |
| distance/control/D対A | A   |   893 |     10 | 12.539754 |  29 |   64 |
| distance/cheap/B対A   | B   |   896 |     10 | 12.437500 |  29 |   64 |
| distance/cheap/B対A   | A   |   898 |      9 | 11.934298 |  26 |   64 |
| distance/cheap/C対A   | C   |   886 |     10 | 11.984199 |  24 |   64 |
| distance/cheap/C対A   | A   |   883 |     10 | 11.534541 |  23 |   64 |
| distance/cheap/D対A   | D   |   881 |     10 | 11.879682 |  23 |   64 |
| distance/cheap/D対A   | A   |   880 |     10 | 11.523864 |  22 |   64 |

全19,804 accepted手で完成snapshotあり、fallback0。各表行は32 game exposuresの実手数分母で、両色nと全histogramはmachine resultへ保存。Aも相手候補ごとに異なる軌跡であり、3対照を同じ局面の繰返しへ置換しない。LMR ONの深さはselective nominal、全幅資格ではない。設定上限64と実到達深さを区別する。

終端前20記録plyとそれ以前のn/中央値/平均も各方法の別viewに保存した。これは実手数proxyで、wall-stock/parent属性は未記録UNKNOWN。軌跡・終盤比・手数・深い尾部の差は平均を膨らませ得るため、中央値/mean/workを勝因や孤立探索性能へ変換しない。

## 192探索：cap-limited wholeと追加削減

原192calls/96sessions/576Mcapは全192 UNKNOWN NodeLimit、実576,000,000nodes、requested D8完了0、completed5..7。同methodの二反復は保存された全root/request/status/depth/valuebits/action/PV/nonclockworkで一致。ABCDDCBA、各既存6root/coldwarm履命・5×2M+1×8Mを維持した元subjectを引用し、新callやcap増加を行っていない。

| 層               | 方法 | whole中央値s |    対A比 | 二pass追加scout実発動 | completed深さ |
| ---------------- | ---- | -----------: | -------: | --------------------: | ------------- |
| nnue/control     | A    | 20.343792227 | 1.000000 |                     0 | [6, 7]        |
| nnue/control     | B    | 20.121919306 | 0.989094 |                 46644 | [6, 7]        |
| nnue/control     | C    | 19.905246955 | 0.978443 |                   210 | [6, 7]        |
| nnue/control     | D    | 19.673867149 | 0.967070 |                 61570 | [6, 7]        |
| nnue/cheap       | A    | 29.215083638 | 1.000000 |                     0 | [5, 6, 7]     |
| nnue/cheap       | B    | 29.665832816 | 1.015429 |                 44258 | [5, 6, 7]     |
| nnue/cheap       | C    | 29.351204746 | 1.004659 |                   210 | [5, 6, 7]     |
| nnue/cheap       | D    | 29.023182492 | 0.993431 |                 57336 | [5, 6, 7]     |
| distance/control | A    |  9.767661978 | 1.000000 |                     0 | [6, 7]        |
| distance/control | B    | 10.436987582 | 1.068525 |                 43848 | [6, 7]        |
| distance/control | C    |  9.798163734 | 1.003123 |                   208 | [6, 7]        |
| distance/control | D    | 10.088926188 | 1.032891 |                 52200 | [6, 7]        |
| distance/cheap   | A    | 18.254753294 | 1.000000 |                     0 | [6, 7]        |
| distance/cheap   | B    | 19.878576831 | 1.088953 |                 43870 | [6, 7]        |
| distance/cheap   | C    | 18.451331256 | 1.010769 |                   210 | [6, 7]        |
| distance/cheap   | D    | 19.665684242 | 1.077291 |                 47104 | [6, 7]        |

wholeはsetup/dropを含む保存scope。TT/gauge・nested clocksを加算しない。NNUE Controlで各候補のwhole中央値はAより小さく、固定Dでは両profileの全候補がAより大きかった。ただし全件D8未完了で、同じnode capでも評価回数・選択木・value/PV等が異なる。従って同仕事speedupやD8完成時間の短縮を意味しない。

LMR追加counterは「追加削減したscoutを実際に開始した回数」で、途中割込みを含む。削減した総ply数・回避仕事・利益ではない。Cはこのcap-limited6rootsで208–210回/二passと少ないが、arenaでは別の手数/深さ/状態分布になり、cap-limited値から実対局での発動頻度を推定しない。source閾値/係数の調整や追加候補は発行しない。

cost192-presentation-v1/{summary.json,roots.json,report-ja.md}と元collection-v3を参照し、保存scalarの192/96/cap/nodes/96反復行/16条件の算術のみ照合。元call RAWは再decodeせず、元collector v1 requestキー誤記・v2 prettyJSON1MiB拒否・v3同cap compact化を維持する。科学再演0。

## 対局terminal work・LMR

| 層/対照               | 側  | terminal n |     nodes | static evals |    delta | 追加scout | LMR trial/通常深さ確認/fullwindow |   PVS |
| --------------------- | --- | ---------: | --------: | -----------: | -------: | --------: | --------------------------------- | ----: |
| nnue/control/B対A     | B   |        807 |  73776848 |     40754933 | 70172860 |    571605 | 2673105/24279/223                 | 22016 |
| nnue/control/B対A     | A   |        809 |  72655175 |     40490501 | 69176659 |         0 | 2686594/16940/187                 | 21799 |
| nnue/control/C対A     | C   |        717 |  63566938 |     36198111 | 60488246 |    245003 | 2484190/23828/196                 | 19260 |
| nnue/control/C対A     | A   |        722 |  64362316 |     36521821 | 61245245 |         0 | 2412625/14926/172                 | 20129 |
| nnue/control/D対A     | D   |        795 |  70505027 |     39400241 | 67095897 |    654475 | 2791654/33028/191                 | 21761 |
| nnue/control/D対A     | A   |        796 |  71559875 |     39711363 | 67900796 |         0 | 2771783/23717/203                 | 21347 |
| nnue/cheap/B対A       | B   |        725 |  40170503 |     22899851 | 38447733 |    331362 | 1488771/11743/133                 | 17332 |
| nnue/cheap/B対A       | A   |        725 |  40300754 |     23158324 | 38724213 |         0 | 1449323/8073/127                  | 17344 |
| nnue/cheap/C対A       | C   |        760 |  43902648 |     23742214 | 41603524 |    184026 | 1597330/8867/132                  | 16535 |
| nnue/cheap/C対A       | A   |        762 |  44122962 |     23831731 | 41863598 |         0 | 1528215/6801/117                  | 16754 |
| nnue/cheap/D対A       | D   |        752 |  42467019 |     23666481 | 40421060 |    431735 | 1631087/8715/110                  | 16093 |
| nnue/cheap/D対A       | A   |        752 |  42891571 |     23955613 | 40894373 |         0 | 1664555/4836/146                  | 16126 |
| distance/control/B対A | B   |        894 | 164905390 |     88751890 |        0 |    738549 | 4535544/35171/112                 |  5961 |
| distance/control/B対A | A   |        891 | 164594964 |     87700383 |        0 |         0 | 4523918/31158/107                 |  5870 |
| distance/control/C対A | C   |        894 | 161278509 |     86433378 |        0 |    328287 | 4489577/51635/95                  |  6041 |
| distance/control/C対A | A   |        892 | 163880953 |     87380433 |        0 |         0 | 4497180/40938/101                 |  5875 |
| distance/control/D対A | D   |        894 | 158403894 |     86578160 |        0 |   1495920 | 5727078/76480/108                 |  6004 |
| distance/control/D対A | A   |        893 | 159831767 |     87125551 |        0 |         0 | 5676940/56038/110                 |  5782 |
| distance/cheap/B対A   | B   |        896 |  75629539 |     40376726 |        0 |    487435 | 2254126/22672/43                  |  4603 |
| distance/cheap/B対A   | A   |        898 |  76445764 |     40904389 |        0 |         0 | 2123017/17089/62                  |  4529 |
| distance/cheap/C対A   | C   |        886 |  74678590 |     39249581 |        0 |    133557 | 2036295/16658/58                  |  4786 |
| distance/cheap/C対A   | A   |        883 |  74796747 |     39523964 |        0 |         0 | 2058941/16226/61                  |  4826 |
| distance/cheap/D対A   | D   |        881 |  74804476 |     39159304 |        0 |    524834 | 2080545/27138/56                  |  4615 |
| distance/cheap/D対A   | A   |        880 |  75114034 |     39100017 |        0 |         0 | 1967827/25463/60                  |  4533 |

全TT/scalarとselected snapshot側のwork/LMR、各field present/null分母、persistent profile sum/gaugeをresult.jsonへ保存した。terminal totalsは最後の未完了iterationの仕事も含み、selected完成snapshotはそのnested viewなので両方を加算しない。追加scoutを含むLMR terminal totalsとpersistent profileを一致照合し、基準Aの追加scoutは0。TT probesも両記録が一致した。

TT requested/effective slotsは全色1,048,576、各色persistent TT retained/capは83,886,128B。これはgaugeでRSSではない。実actual method ID/namespace/reduction_rule/requested nameをnative profileと各accepted手で一致確認した。PythonのID/suffix builderはない。image b9d515e7/Build1af3ad9e/source qualificationを再審査せず、model/image payloadは開いていない。

## receipt・drain・終了

100ms main authority receipt/5ms reserve、node safety1M/depth64/maxply200、AI2+6/main4。全19,804 acceptedでreceipt<caller start+100ms、合法、matching terminal回収、inflight=0。receipt late/equal0、failure/engine_error/forfeit/fallback/first receipt-control error/completed snapshot validation error0。terminal returnがdeadline以上1,491件、commitがdeadline以上1,675件は、receiptの遅延と区別して保持する。

各方法のreceipt slack/terminal drain/caller/thinking時間、停止reason、reserve_stop_is_not_user_cancel（全件true）をmachine resultへ保存。cancelledというsearch stopをuser cancelへ変換しない。全native all_workers_joined、main PID/TID/管理core4・各AI core/TID、terminal→collection→return順を元記録で照合した。

物理NNforward、continuous family RSS、孤立eval/LMR費、all-process Search CPU、全作業費はUNKNOWN。general nn_calls=0やstatic_evaluationsを物理forward数へ読み替えない。native peak RSSは原scopeで保持し、連続family peakと呼ばない。

## 参照・検証・費用・STOP

settings afdcf640/6200、plan/schedule、12config/Experiments/manifests、12組publication/native manifest/RAWをparse前後のSHA-size-modeで束縛。各gzipはbounded streamingで1対局ずつ読み、単一member/rawSHA/bytes/改行・record上限・元journal prefixSHA/bytesを照合。既存arena_observationを再用し、geometry/Searchを再実行していない。原384journalのdecodeは一度。

保存arena reader STOP 2026-10-15T10:51:20.892399+00:00、小cost/metadata mark（final ref再照合前） 2026-10-15T10:54:22.897778+00:00。directwait/reap/fresh exact IDs/no_new_privs/handles/TMP/owned[]はSTOP.json、全FileRefsはselected-refs.json/completion.json、OWN affected usageはusage.json。

今回arena解析child wall 1.332104218s、self ru_maxrss 38653952B。原arena outer1989.2591725599923s、原cost outer750.297630404006sは別の実行scopeであり、nested時間を重複加算しない。guard/controller/captureの費とreturned対disk masksを別receiptに保持する。

CPU10/guardian14、child960MiB+controller64MiB=family1GiB/GPU0/hostreserve4GiB、AS capなし。fresh topology/allowed cpuset/readback/no_new_privs=1はcontrollerと実launch receiptへ保存。affinityだけで公平timingを認定しない。新source/build/数学jobを発行せず、維持されたfiniteexecuteで保存helperのみを走らせた。

本人leafはwrapper ready/showで実ID413.4/assignee01a11062を確認（実statusはopen、更新はRoot-only）。Main/Git/index/Cargo/Beads/status/backup/closeは324所有。元414/412/413draftを変更・再送していない。新Search/対局/モデル/forward/solver/52suite/新bootstrap/追加sampling/fit/scale/cap調整0。Rootだけが同関連maxへ必要結果を配分し、作者reviewdispatch0。

全mixed/learnerALLprep/pipelineと323 USERPAUSE、productgeneratorenableOFF、models/defaults/weights/seals/oldfits96/foreign/全旧RAWFAILED費UNKNOWNとdecimal50GBを保持する。

時刻erratum：machineのpresentation_reader_STOPは最終selected-ref再hashより直前のmarkであり、実reader閉鎖UTCとはしない。元fieldを保持しtimestamp_erratumで意味を訂正した。cost helperのexact exitUTCはUNKNOWN、directwait/returned receiptとSTOP.jsonのfresh原identity absentで実閉鎖を確認する。arena reader_STOPは全posthash後で変更0。
