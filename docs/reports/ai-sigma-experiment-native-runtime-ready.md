# 170 修復native運用と4arena費用の有限確認

`quoridor-4lc.170`、experiment、契約b6191701/親11。受領観測2026-10-03 05:50:22UTC、165最小pack/Git復元/backup/handoff終了後05:52:57 claim・静的開始。処理06:35:22/新heavy06:25:22/提出06:50:22、親早側を維持。旧165の科学・16局・source・modelはreadonly。新build/依存取得/Chrome/game/学習/GPU/NNUE追加0。

前165修復a78ea833を必要最小loader/controllerで再利用し、元native binary166dd0c4・ONNX d790dac6・固定Web751186・native CPU ORT1.30.0を維持した。専用engine2process/session2/arena、intra/inter1・SEQUENTIAL、両engine共通setImmediate IPC drain。NN前のactual route K8 oracle・402境界・false/error/unknown→spawn0を確認。admission mockのharness失敗2件も保存し、科学取得の失敗へ付替えていない。

保存initial-p1/asym-hv-p2各C,R,R,C、solo8と条件付き4arena32の**全40要求を1回ずつ**実施、すべてCOMPLETE。fresh tree/held sessions、各phase共通barrierから開始、同controller monotonicでt0/CP受信/合法検査・clone・cache代入完了/公開/返却を記録。actualend<=402のcertified cacheのみ、411予定/public<=500、跨ぎ・unknownはrollback、旧NN回収を原因側cleanupとして次t0前に完了した。根features648/NN137 f32bitsは両engine・両mode・各core・各入力でexact一致。policy/PUCT/FPU/f64/合法順/モデル変更0。thin loaderのNN resource guardは事前204/request×40=8160（未配分32、全手上限8192）、到達ならtyped未知。今回は到達なし。

| 計測 | solo CPU2 | 4arena CPU2/4/6/8 |
| --- | ---: | ---: |
| 完成予定要求 | 8/8 | 32/32 |
| 手NN / startup別 | 398 / 2 | 2093 / 8 |
| outer job秒 | 5.723927 | 6.547816 |
| init等を含むruntime秒 | 3.736830 | 3.922154 |
| 要求phase wall秒 | 3.311918 | 3.378213 |
| 最大public ms | 414.893 | 415.200 |
| 最大実admit完了 ms | 400.290 | 401.457 |
| 最大public後cleanup ms | 2.531 | 10.494 |
| pending取消返却discard観測要求 | 7/8 | 25/32 |
| owned+guardian current RSS peak bytes | 619491328 | 1686081536 |

phase wallからの参考batch係数は3.92150、outer全費では3.49669。API・NN pipe・初CP配送・採用K/NN・completed/terminal・準備/初期化/warm・cleanupはcore/engine/入力別にresultsへ保存し、区間の包含を二重加算しない。4arenaもt0は準備完了後の各controller入力開始で、barrierからの開始offset最大12.864msを保存し厳密同時刻としない。

core2 steadyの保存採用Kは候補initial37→27/asym36→30、参照initial40→37/asym41→34（solo→parallel）。4arena内で管理もCPU2に載る費用・core性能/負荷/順序等が混在する。並列をsoloと同じ探索量・無影響としない。他coreにはsolo対応取得がない。異なるケース/engineの総NN比を棋力因果へ換算しない。参考batch係数はWDL倍率・大標本完走保証ではなく、旧165の2.22局/分へ掛けて正式1200局の時間を断定しない。

直前admissionで旧165 exactidentity不在、current外heavy/短計算/RSS/headroom、cpusetと異なるphysical core、scheduler現在identity/次通常observeと65秒余裕を確認し保存した。92 affinity/設定は変更0、LLM active数を入口にしない。全観測owned TIDは各許可pool、parent計算CPU4/RAM8GiB内。parent/currentRSSとinstant peak・全期保証を区別する。

実NN pending取消discardを32要求で観測、残8要求はcoverage欠測のまま、追加反復0。startedは実infer前count、returnedは終了span、discardedはstop観測後返却でbackup/新探索へ不採用、worker completedは採用cacheとは別。Model/source対応とreturn zeroを有限確認したが、exactkernelCPU・全TIDの推論寄与・OS時計校正は未成立。この2根でterminal-only **実ORT**取消coverageを一般保証せず、165人工NN0結果と分離する。`formal_ready=false`、機能有限成立と正式NIを区別する。

科学stopはscience-stop.json SHA `b3e9abb87275a1c155b3f8f7efdb31c66972409dc3e92aebad5c507d4e8dde4e`、runtime source `bd7ffde0d46f51ec35d8faa4091f526c95ccc914`。手NN合計2491/startup10別、heavy12.271743秒/上限120、mock jobは別管理。全attempt/版/command/typed control・監視late failure経路・Model EOF/engineclosed/searchzero/main timers・outer ownedwait/currentidentityを保存。現在不在を自然/全期間/全host停止保証へ格上げない。

新scope guard7MiB内で保存するため、停止済みの重複progress snapshotのみ、最終result.rows＋保存group時刻から元bytes完全再構成・hash一致・再構成metadata Git保存/復元を確認後に整理した。原最終resultと全attempt、旧165/149/151証拠は保持。raw archiveの全member readback/有限実展開とsource/input/Git bytes確認、Beads notes/backupを最小引渡しに含める。外部cached Python/Cargo/模型をGitだけで復元可能とはしない。

**最大1次案：この4arenaを選定候補として、別配分の小native教師生成・既schemaへのπ/rootmean/z/lineage exportへ進む。** 4arenaのRAMと短runtimeは成立した一方、core2の探索量低下とsample/時計射程があるため同modeを結果前に固定する。sampler・game総費・独立splitの必要未実装をその小単位で測り、runtime計測を自動連鎖しない。正式NIには新native版/mode/独立開始分布/fault全分母/固定m・停止の登録が別途必要で、今枠残費から600pair/1200gameの完走を約束しない。

保存移管erratum：科学jobの保存peakはguard内だが、停止後Git移管のprivateindex実380127bytesを131072bytesと見積った。保存済current5980160＋新archive Git blob allocated1024000＋index380127から、移管時の下限7384287bytes（guard7340032を44255bytes超過）を導出した。連続peakは未サンプル。`storage-transfer-erratum.json`をtyped保存不足として保持し、全期間guard成功に格上げない。科学40行・時計・勝敗分類へ付替え0、新NN0。indexは除去済み、残る小metadataのGit保存はin-memory subtree方式に変更し、親予約追加なしでbackup/最小引渡しのみ行う。
