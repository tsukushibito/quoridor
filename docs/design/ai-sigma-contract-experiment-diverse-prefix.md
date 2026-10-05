# SIGMA-DIVERSE-PREFIX / quoridor-4lc.119 / 契約1・枠8

coordinator→既experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746単独writerへ実依頼。ユーザーCPU Sigma比較継続と枠8内の通常配分。117/118停止保存を有限受入れ済み、原成果を変更しない。親現行枠8/common/experiment/実行記録規約と本全文、ready/show goal/self・pauseなし/本人担当確認後119のみclaim、受領開始を統括へ報告。同saved/model/effort/cwd、セッション数拒否なし・同役二重起動なし。

## 問いと結果前条件
117の固定3fixture×2seedでは全pairで固定色が勝った。今回、AIを使わず生成した合法prefixで候補C1.5対固定Sigmaの先後別WDL、初回完成手/採用/残処理の不足を広げて診断する。モデル/探索係数/FPU/order/tie/finish/caps/ORT/時計を変えず、旧診断と成績を混合しない。正式holdout/NIと呼ばない。

候補immutableC1.5 Wasm SHA1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01、同ONNX d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、ORT1.21.0 CPU/Wasm、固定Sigma C1/FPU.2/first tie/temp0等を維持。seed探索1979を全局へ固定し、prefix生成seedと区別する。browser mainが対局/合法性/勝敗/時計/結果、専用2Worker各model/session/generation/SAB/controlで手番側だけ新探索、Nodeは外起動・監視回収・終了後保存。T500/cutoff402/adopt411、bounded readを維持。

確定後旧Workerの新評価を抑止し返却discard/次木非再利用。相手通知/t0は旧ACK・詳細診断を一律に待たず、自Worker次開始だけ自己旧zero後。現在ready-relative診断t0と自待ち/input availableを別記、116将来F時計へ結果後換算しない。Worker停止/ACKwall/APIawaitを追加有効思考や内核CPU・正式同実効cycleと呼ばない。

## 入力生成と最大16局
ブラウザ内RuleAで初期局面から生成する。固定pair順1〜8の生成seedは31001,31002,31003,31004,31005,31006,31007,31008、prefix目標plyは4,5,8,9,12,13,16,17。各prefixは同局面/履歴で候補色1→2の2game、探索seed1979、最大8pair16game起動。P1/P2開始を各4prefixにし、既3fixtureへ戻さない。

PRNGはxorshift32（x ^= x<<13; x ^= x>>>17; x ^= x<<5、各unsigned32）。生成では合法pawnと合法wallを分類し、両方あれば各.5でclassを選び、そのclassのRuleA合法順から次乱数で一様index選択。片方空は他class。class判定/乱数消費/選択順をsource/preregisterへ明記。合法集合が空・途中goal/draw・重複prefixはAIなしで棄却し、各pair最大32attempt。attempt0は指定seed、attempt aは(seed XOR ((0x9e3779b9*a) mod2^32)) unsigned（0なら1）。全生成attempt・棄却理由・採用prefix/history/key/seedを保存する。採用は最初の非終端・合法・非重複prefix、候補NN/勝敗/価値で選別しない。32attemptで得られないpairは未開始、不都合な入力を別分布へ救済しない。

全8prefixをbrowser内生成・replay検査して固定SHA/config/preregisterを保存してからAIモデルをloadする。生成器の不具合はNN前に同scopeで修正可、生成版・旧失敗を保存。prefix/入力を選定診断として扱い将来正式holdoutへ流用しない。元の実ルール共有による独立性限界は明記。固定prefixを別履歴へ省略しない。

各局はgoal優先、総ply200上限。全attempt/開始・未開始/goal/draw/初回無し・late/engine fault責任loss/shared timer/Judge/identity/automation unfinishedを維持し、原受入れ責任規則（候補NNloss/参照NNinvalid）を明記。良い結果の再試行置換/補充0。debug反復は許可するが既起動game capを減らさず元成績救済しない。時刻・数値欠測は未確認、0補完なし。

## 所有・必要な修正と確認
self write tools/ai-sigma-diverse-prefix/、.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX/、research-data/ai-sigma/119-diverse-prefix/、docs/reports/ai-sigma-experiment-diverse-prefix.md。原117/118/112sourceと結果、共通model/kernel/common/registry/92runtime/default Git indexへ書込0。必要glue/設定/runnerだけ自己域に置き、readonly import・Git/archive必要参照。全copy/全史再gate/モデル再取得なし。新build/依存導入/GPU/学習/host変更/製品統合/pushなし。

先に117pair4のheavy admission helper falsepositiveとエラー後launch継続を自己runnerで修正する。helperは実exe/argvで研究heavyを判別し、読むだけのmetadata/MCPをheavyと誤認しない。一方helper timeout/parse/不明owner/未知状態は起動不可として返し、シェル起動列がその失敗を跨いでlaunchしない。重job実在・metadataのみ・読取エラー・停止未確認の少数mockで判断とlaunch0を確認する。旧pair4事前gateを遡及成功へ変更しない。実job直前に新headroom/外heavy/自身旧回収・保存forecast確認を保存、同親CPU/RAM内で直列に起動する。

必要なprefix/identity/seed/P2/mock/設定・構文を安く先行。実接続の追加要求は最大2（最初の新prefix両engineをモデルとmain経路で確認、全分母を別記）で十分。受入れ112/113/117/118の7機能/全旧棋譜/NN数値全反復を先行gateにしない。差分が少なく静的/mockで成立すれば直接固定pairへ進んでよい。

各pairに全棋譜/公開/採用sequence/初回CP/予定と実adopt/t1/自己wait/input/t0/旧返却discard/相手t0<旧ACK/新API入口と旧返却を保存。startupと手NN/completed backup・depth/capの保存可能な量を別記する。start/end Workerclockを保存し途中drift限界を残す。詳細数値/棋譜検査はbrowser内で対局後に行い、対局deadline経路へ重い検査/保存を加えない。少数rootはP1/P2両engineを含む結果前選定規則にし、固定参照と動的自己整合を分ける。新入力のrootに固定golden参照があると偽称しない。全深部一般一致を主張しない。

118のAtomic publication近傍時刻提案は今回は保留。markerをexactstore時刻へ変更しない。「全SAB書込402前」保証を今回の目標や前提にしない。新prefixの採用期限/初回無し/競合の有限観測を得るのが目的、共通化のためにNode審判へ戻さない。

## 配分・終了
静的CPU0/RAM1GiB guard896MiB/各60秒・累計600秒。全Chrome NN0含むCPU[2]単logical、各ORT1thread、2session/親+所有子のcurrentRSS RAM6GiB guard5.5GiB=5905580032B。各browser600秒/累計重3600秒、他heavyと直列。92 CPU0/RAM1GiBと親CPU4/RAM8内。

新自己保存128MiB guard112MiBは既experiment entry2GiB内/親保存12GiB追加0。実現在保持＋有効予約未使用分とprefix/log/temp/Git/圧縮中peakを確認、各pair必要Git archive復元後に所有展開重複を整理可（他読み手/共有モデル/原archive削除0）。測定中の圧縮/他重jobを避ける。全16開始/各総ply200=最大3200対局公開、機能最大2別分母。

実処理は受領65分又は13:00UTCの早い方、新runは受領60分又は12:55、提出受領80分又は13:15の早い方。親14:05:49新重job/14:10:49監督/14:13:49monitor/14:15:49枠終了不変。最初の本人開始・prefix固定/起動前helper成立・対局開始、その後2pairごと全分母/停止と保存を短く報告。資源/所有/pause/回収不能では停止、未実施と不足を示す。

最終source/NN/両Model/search/timer/monitor停止・hashafter、inner controlled/outer ownedwait/currentidentityを分ける。必要source/Git/config/command/全失敗/棋譜/clock/resources/生成attempt/archive復元、短報告・Beads backup→coordinator。判定支持/不支持/不成立/未完了と残課題を返す。formalNI/Sigma/actual_go自己発行0、goal他者close0。重大な主張の必要独立確認は統括が停止版へ後で配分、毎run新issue/新独立層/一NN窓を追加しない。
