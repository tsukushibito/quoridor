# SIGMA-BOUNDED-WALLLESS-ORACLE / quoridor-4lc.142 / 契約1・枠9

既hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418→coordinator。140の次提案を変更採用し、設計だけでなく小さい有限ラベルをNN0で構成する。問いは、浅い即goal・最大priorだけでpassした129より先の手を必要とする、policyに依存しない勝敗の区別を限られた費用で得られるか。両壁資源0の合法小終盤なら壁分岐を外して有限minimaxを試せるが、一般中盤/戦略への代表性はない。FPU再試行や既gameの結果選別をしない。141裁定待ちは開始gate0、140/source実Runtime停止後の新scope。

対象はAIなしで生成する最大2固定局面（P1/P2各1を目安、不成立なら欠測）。initial Stateから全手RuleA合法確認で進め、両player壁remaining0・非終端を満たす合法historyを作る。壁20枚を合法に消費し、pawnを近いrace/交差corridorへ進める2つの幾何規則と順・seed（41001/41002）・各attempt最大4・prefix最大160ply・終端/不適合拒否条件をNN0生成前にpreregisterへ固定する。担当は具体幾何規則の通常設計を自律判断できるが、生成ラベル/未来AI結果を見て規則変更や入力追加0。各case最初の適合局面を採用し棄却含む全attemptを保存。直接board/壁counts/turn/history改変0、存在しない到達可能性を仮定しない。両壁0が作れなければ代替壁残状態へ拡大せず未成立で終了。generationにcandidate/Sigma/model/value/priorを用いない。

生成と合法性/ラベルはChromium browser mainで実施、Nodeは起動/外監視/回収/終了後保存。モデル/AI探索Worker/SAB探索要求/NNは起動0。既RuleAを必要script参照し共有source編集0、独立ルール実装の正しさ証明でない。history/key/side/featuresbits/全prefix/原rule hashとactual-served sourceを保存し、後続AI評価の入力とラベルを区別する。

採用入力ごとにroot全合法pawn手を列挙する有限adversarial minimax。最大深さ6ply（rootから適用手数）・rootを含む適用node最大20000/入力、時計watchdog20秒/入力を結果前固定し延長0。両壁0の合法集合を通常RuleAで取り、jump/diagonal/history/repetition/actualgoal/draw/手番を実stateで判定。rootplayer payoffにterminal win1/loss−1、true RuleA draw0。depth/node/time上限は未解決区間[-1,1]で、heuristic/未探索を0/draw/lossへ変換しない。root各Actionにsound lower/upper intervalを返し、自turn max/相手turn minの分母と交互視点を確認。pruning/cacheを使うならbound型とdepth/history込みkeyの正当性を小fixtureで確認し、全root Actionの値の範囲/未解決を記録、勝ち枝だけ選んで完成とは呼ばない。証明witness/必要counterexample/terminal数/depth/capstopを保存する。即goalだけで全判別が終わる入力は自明と分類し別入力補充0。

目的はNN0ラベルの成立を測ることで、AI性能を今回判定しない。rootに複数の合法Actionがあり、即goalなしで多手先の異なるcertified payoff又は一部certified勝ちと他certified負けが得られれば非自明な小尺度候補。全同点/全未解決/一手だけ既知と他未解決ならその限界を返す。AI最大prior/root1を読んでいないため小改修感度は未校正、後続独立label確認と別AI比較は統括の新配分のみ。浅い既129をdepth拡張の成功と呼ばず、壁なしraceの局所・有限範囲と一般棋力を分ける。

上限停止/terminal/視点/jump/履歴cache/unknown区間伝播をNN前小mockで確認、実wrapperはadmission false/unknown/readerror/ownership/期限時spawn0の同必須分岐。CPU0静的/mocks単1/RAM1GiB guard896/各60秒/累計180秒。全browser NN0はCPU[2]単1/RAM6guard5.5/各job90秒/累計120秒、startupモデル0。141はCPU0静的/RAM512で並行可、他heavyは直前確認しChrome直列。起動前140最終stop/currentidentity/外heavy/current RSS/headroom/保存forecastを確認、他owner signal0。入場数gate0。case初回科学成功を不必要に反復0、普通debug失敗と未開始caseの修復は同budget/固定条件内、失敗を成功へ置換0。

自scope tools/ai-sigma-wallless-oracle/、research-data/ai-sigma/142-wallless-oracle/、.artifacts/ai-sigma/resume-20261002/WALLLESS-ORACLE/、docs/reports/ai-sigma-hypothesis-wallless-oracle.md。既hypothesis16MiB/combined14MiB guard内、新scope2MiB目安（旧保守8908800Bを再測定なし減額0、packedGit/raw/Chrome tempもforecast）。全copy/原archive展開0、新親予約0。guard不足なら起動せず不足を返す。共有host/browser設定/toolchain/download0。必要wrapper/依存は既個人scopeの所有停止済recipeから最小再利用し、原編集0。

処理受領40分又は20:00UTC、新heavy受領35分又は19:55UTC、提出受領55分又は20:15UTC早側。本文前browser/Node/timer/monitorcallback/innercontrolled/outerownedwait remainingunknown0/現在identity/sourcehashを別保存しheavy停止先報、全生成attempt/label/未解決/command/Git/hash/clock/資源/最小archive復元/backup。成功/未成立/予算未完了いずれも停止記録で引渡し。最大1後続案と、非自明区別が得られない場合の枝終了を返す。別配分なしにNN/model/gameを開始しない。

現在親枠9/common/担当role/研究目標/記録規約全文を継承。worktree /workspaces/quoridor/.worktree/ai-sigma、既saved同model/effort/cwd。ready/show goal+self/pauseなし本人担当後自issueだけclaim、実受領/開始を短く報告。普通debugは同scope/総予算内で失敗/版/runを保存、元科学結果の成功付替え/有利な入力補充0。原140/139/134/127/全過去成果/共有crates/model/role/registry/92/defaultindex/mainはreadonly。他owner signal/interrupt0、新NN/モデルload/AI探索Worker/game/rollout/build/取得/GPU/学習/委譲0。親CPU4logical/RAM8GiB/保持＋未使用予約12GiB/23:10:59新重job/23:15:59監督/23:18:59monitor/23:20:59終了を維持。自己source/process停止、版/入力参照/hash/run/command/開始終了/全attempt/必要結果/資源と欠測/最小復元/Git/backup/reportをcoordinatorへ。現在不在≠自然全期間全host、formalNI/Sigma/actualgo/政策採用/goal他者close0。契約writer coordinator、担当は自域のみ単独writer。提案から後続AI評価を自動開始しない。
