# SIGMA-ROOT-FACTOR-CORRECT-N / quoridor-4lc.79

試行1・契約1、hypothesis `01a0f31c-2e4b-7170-82c5-69e1428c2418` → coordinator。親継続版2全文 SHA `6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f` 継承。ready/show/pauseなし・本人claim、最初のUTC読取受領22:32:10.117788、処理22:52:10.117788／新job22:47:10.117788／提出23:02:10.117788（絶対期限との早い方）。厳密な配送時刻・初期短コマンド観測は欠測として保持。.78の26hash/write-stop・統括hypothesis78-review.jsonの限定受入れを確認し、未確認をnotes保持して本人.78だけclose。目標・他担当close0。

**正Nの保存根診断は有限支持。原finish765/765が一致し、C・sqrt・scoretieの一因子変更で仮想次argmaxが46／19／114根変わった。** 旧v1の28／9／117は別N式の結果として保持する。変更後全探索・実際の次select・棋力・採用・NI・目標達成は認定0。NN/Chromium/全MCTS/対局/holdout/GPU/Cargo/依存取得/委譲0、actual_go=false。自己検算であり他役独立受入れ待ち。

観測は旧765正常completed checkpointのedge訪問和と保存simで、全件 `edge_sum+1=sim`。固定sourceのfresh root初期値とstep/simulate/backupから `node.visits=sim` を条件付き復元した。**直接raw node.visits観測ではない。** baselineは `sqrt(node.visits+1)=sqrt(edge_sum+2)`、C1.5/Q0/seed1979 scoretie/候補順/f32。入力headerをedge_sumとNに分け、`sum(edges)=edge_sum` と `N=edge_sum+1` を独立検査する。旧v2のsum=n assert/exit101は不変で、再集計未実行を効果ゼロへ付け替えない。source/count根拠は[source-count-proof.json](../../.artifacts/ai-sigma/continuation-20261001/SIGMA-ROOT-FACTOR-CORRECT-N/source-count-proof.json)。parentQは全765欠測、実FPU適用・edge平均補完・旧人工8根混合0。

結果前[preregister.json](../../.artifacts/ai-sigma/continuation-20261001/SIGMA-ROOT-FACTOR-CORRECT-N/preregister.json)へ3対照/分母/入力SHA/checker Rust・JS sourceSHAを保存し、compile後のbinary SHAもfactor前に固定した。input SHA `05c9c28327fa73ba7265a979c22697c4ae0f61efc40b82e82f9ffbb37f000c81`、binary SHA `6fccab05677c4e3c9600965db531b931f7cb8148bac1053c4f968147547a3ff6`。必要な765根だけをbits付き一個の入力へ、metadataは参照用に小さく保存。全raw/model/tree複製0。旧sourceのtie・finish比較式・select f32式をimmutable edgeへadaptし、original visits→prior.total_cmp→seed tieを保持。Rust1.98.1のstd-only一回compile、Cargo/rootlock更新0。

先gateは入力件数765・Action0..208/一意/参照合法順rank・seed・finite prior/value・f32bits往復・expectedAction集合。boundaryはsum/node分離、singleton、負value許可、負prior/NaN/Inf/空集合/rank/Action範囲拒否、負N/不正整数/誤count拒否。後者3のexit101は期待した入力拒否で、checker失敗や効果negativeではない。独立finish-only jobで765/765を確認した後にfactor出力。追加finish ablationは実行0。helper訂正・再compile・成功標本の再試行0。

| 一因子の仮想次argmax変化 | 全765 | accepted764 | native371 | Wasm394 | matched97組の194根 |
| --- | ---: | ---: | ---: | ---: | ---: |
| C1.5→1.0、他固定 | 46 | 46 | 16 | 30 | 23 |
| sqrt(N+1)→sqrt(N)、他固定 | 19 | 19 | 7 | 12 | 10 |
| score同値seed→候補順first、他固定 | 114 | 114 | 84 | 30 | 39 |
| first固定で候補順→参照合法順 | 76 | 76 | 61 | 15 | 29 |
| seed/candidate順→first/参照順の束 | 109 | 109 | 78 | 31 | 38 |

最後2列の方式は3基本対照と別に保存した。first固定の順因子とtie＋順の束を同一因子と呼ばず、件数を加算して効果としない。private lateはgame5 ply34の1根で全対照変化0、全765へ含めるがaccepted分母へ入れない。無応答game3の根欠測1を補完・除外成功・遅配救済0。matchedは旧同context97組でnative97/Wasm97、C変化6/17、sqrt5/5、tie39/0。互いのbaseline仮想次Action一致34/97、C1は36/97、他列34/97。原finish/公開Action一致83/97とは意味が異なり、36への変化を棋力改善と呼ばない。

全765×5列＝3825選択について、別JS Math.fround・BigInt wrapping tie/total_cmpでAction、selected score/margin bits、ties/near/visitsと**全edge score bits243,850個がRust f32と厳密一致**、許容差0bits・結果後変更0。JSNumber無丸めは選択score bits1026/3825差、選択Action差0、この標本限定。baseline exact tie122根／near tie123根／未訪問選択264、margin中央値.04215328395366669（n762）、singleton3はnullとして保存。Infinityを有限marginのように集計しない。

同765根でN復元によるbaseline自体のAction変化19、scorebits変化765、ties/near変化各3、chosen_visits変化19。旧v1 Cの28根は新46に含まれ18追加、sqrtは旧9をそのまま新19へ足したものではなく変更集合が入れ替わる。tie117→114、first固定順78→76。旧v1/v2・旧27/32rawの結果を上書きせず、旧logを読んだ差を[v1-baseline-method-difference.json](../../.artifacts/ai-sigma/continuation-20261001/SIGMA-ROOT-FACTOR-CORRECT-N/v1-baseline-method-difference.json)とsummaryのchanged IDsへ保存した。

H2のC/tie/orderが固定snapshotの次選択へ影響する有限根拠を得た。H1 backend/丸め/探索速度は今回NNを呼んでおらず判別していない。両仮説は競合する説明であって排他的ではない。native/Wasmの根は同じ履歴でも既存探索量/累積value/順序が異なり、matched集計だけでbackendが差の原因とはしない。複数ply/rootは独立標本ではなく、765という数をWDL精度に使わない。次の最小案は同backend/seed/value/order・固定3goldenでCだけ変えた等completed-simの分布診断、または同features・同CPU/threadでのbackend単独NN内訳比較。いずれも別契約と独立gateが必要で、今回は実行・係数採用0。parentQを取得できない実根でFPU説を否定せず、深い木/終盤/全H2を外挿0。

再現は別新scope/独立契約へコピーし、固定原成果へ上書きしない。compile commandは `rustc --edition=2021 -C opt-level=0 -C codegen-units=1 -C debuginfo=0 -C strip=symbols tools/ai-sigma-root-factor-correct-n/checker.rs -o <scope>/checker`。監視付き順序はsupervise.pyのcompile→boundary.py→checker roots-input.txt --gate→checker roots-input.txt→Node verify.cjs→rustc --version→compare-v1.py。各job60秒以下、CPU0、UV_NO_SYNC/OFFLINE/PYTHONDONTWRITEBYTECODE=1、専用TMP/XDG、Nodeheap192＋RSSguard896MiB、AS1GiB0。preregister/source/commandhash・UTC/monotonic/boot/PIDstarttick・TIDaffinity/RSS/exitは*.started/process/logに保存。factors.logは全edgebits、selected-results.json/summary.jsonはcompact結果、boundary-check.jsonは失敗拒否証拠。

本文前22:42:14 UTCにsource/runtime-stopとinput-afterを保存。7監視job exit0/guard0、記録15identity現在不在、全管理job終了。一回compile／全観測TID CPU0／20ms観測parent+descendants RSS最大152,162,304B、監視CPU累計.867594秒/jobwall約.932970秒。短いlinker/boundary childのPID/RSS・初期読取/claim/生成の副次CPU・瞬間peak・全期間affinityは欠測を0補完せず、自然停止/全期間証明へ格上げしない。取得input21afterと旧78manifest26不変、旧28manifestのroots/source/原log/summaryの4実hashも一致。初期filename/構造読取は新before ledger以前で、ledgerは入力変換/compile/factor以前。旧manifestとの明示照合は最後に追加したため、最初の読取前の局所hash捕捉を主張しない。ソース・binaryはhash固定。HEAD1482df8…c76/codex/ai-sigma、HEADだけでは入力同定不可。

旧78全保持＋本scope＋双方報告のcombined停止前5,488,640B、14MiBguard/16MiB共有予約内。最終metadata分はmanifestへ。追加予約0、旧32返却0、cum12GiB減額/reset0、全owner現在量の証明0。原raw/失敗削除0。書込み/自己runtime停止後pause/show/backup/report、自.79は独立受入れ待ちin_progress、本人.79/goal/他者close0。Atract/BORT/CB0・H1/H2/H3/H4、旧m48/m32 no-go・m8不採択・旧32局非統合/NI未立証/Sigma未達、旧容量期限scopeRSSaffinity・g287/62+82/340秒/2.26秒/6196ms・true合法200/no-legal/deep/rawview/entropy/training来歴未確認を保持する。
