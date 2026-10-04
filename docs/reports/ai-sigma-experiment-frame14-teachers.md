# frame14 independent staged teachers / quoridor-4lc.194

新fresh144gameを全予定一度だけ生成し、144GOAL/6996適格教師行を保存した。train96=4653行、validation24=1248行、test24=1095行。trainの入れ子24/48/96は1217/2345/4653行、validation/testは全段固定。6jobのproduction総jobwallは691.356145s、Rpolicy/Rz/Rjointはいずれも10.119242行/s。これは生産jobの初期化・入力・探索・NN・輸送・記録・回収込みの率で、準備・NN0export・Git/backupを含む全pipeline時間と区別する。

| job | 全24予定status | Rpolicy | Rz | Rjoint | 全job秒 | 物理手NN |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| train01 | 24 GOAL | 1217 | 1217 | 1217 | 122.708701 | 68292 |
| validation | 24 GOAL | 1248 | 1248 | 1248 | 121.714179 | 72076 |
| test | 24 GOAL | 1095 | 1095 | 1095 | 102.083891 | 61999 |
| train02 | 24 GOAL | 1128 | 1128 | 1128 | 116.627886 | 64045 |
| train03 | 24 GOAL | 1190 | 1190 | 1190 | 111.675072 | 68093 |
| train04 | 24 GOAL | 1118 | 1118 | 1118 | 116.546417 | 62507 |

全144slotのterminal/打切り/手数分布を `all144-status.json` / `generation-summary.json` に保持した。打切り/欠測は今回0、全正常GOAL。原RuleAのdraw/newply200capとtypedfaultのz未知/value loss maskfalseは条件として保持し、好都合なgame補充/成功再実行は0。

結果前のentropy/domain、144seed/family/actionseed/slot/partition/openingは `openings.json`（SHA9588613de2e4c0b7fb1c57d836419be7b1e973240833bb41c84a7e8f1101bcac）。8/12/16/20/24/28plyを各split均衡、単一pawn/wallカテゴリ各.5/内一様、chosen-emptyカテゴリ又は途中/最終terminalで全proposal拒否、最大256/firstaccepted。oldteacher/旧173正式holdoutの入力/ラベルを利用していない。偶然の共通局面と代表性の保証は別で、初期0plyを避けたこの抽出分布の有限データである。

readonly187 worker/Registry binary166dd0c4/provider/checker/capを再用。3worker core2,4,6+provider/broker0、各game1pending/独立tree/maxB8/flush target.25ms/FIFO/7identity、K64 rootN64 edgeSum63、tau1初16newply以後strictfirstargmax。π=visit/63を実sampling行動onehotへ変更せず、rootNN/rootmean/leafNN/z/STM/P1/合法209→canonical136とhistory/lineageを区別して全手保存した。固定ONNXd790のreadonly foldedCUDA dynamicB/f32/TF32AMPoff、原ONNX batch1を変更せず原cap307200/jobも維持。全物理手NN397012、startup forward0/debugforward0、session/model initは各jobの実費に含む。provider/broker returned/discard/zero・partial batch/queue/pipe/init/cleanupはraw archive/summaryに保存し、await重複をkernelCPUや排他分解にしない。

共有RuleAの全6996行replayでfeatures/history/合法順/行動/P2変換/π/root64edge63/terminalwinner/z視点を確認した。これは独立ルール証明・教師真値・全deep tree対応・棋力NIではない。今回の主成果は新教師の実取得で、旧187の効率診断を再測定していない。

共有195 `export_generated.cjs` → `frame14.py canonicalize/mask`（停止/hash束縛6files）を194本人がNN0で実行した。実forwardと共通の `frame14_data.canonical_model_input` を使い、QF1-f32-STM-v1/STM・相手のsortedIDs/同順f32距離bitsに署名した。historyはRuleA-state-history-v1+対象state+side+sortedcounts。maskはstate OR history OR実QF1入力共有、最大train96をval基準、train96+全valをtest基準にし、target/z/lossやvalidation結果を使わず設定選定/候補freeze/test評価の前に固定した。fixedmask SHA `10b502cd9e1c5334e56a3f460ef3edff7f822c8f52f69c3af53529c67c45d5f5`。

現有限データでは全144familyがunique、crossgame/crosspartition state/history/QF1共有0。state/QF1は各6981unique（6996行中15重複は同game内）、history6996unique。validationは1248/1248eligible、test1095/1095eligible、各全24予定/G+=24/0eligiblegame0。未見game全体・条件付き未露出row subset・IID/通常対局代表性・教師品質の主張は分ける。0eligibleが生じた場合にも全分母/除外件数を残す規則は保持。

使用可能正本は `research-data/ai-sigma/frame14-teachers/final-qf1-v2/dataset-manifest.json`。all144-metadataはlabel-free、training-labelsはtrain+val5901行だけ。専用testラベル・教師・rawはtest-sealed内。混在fullstatus all144-status.jsonにもtestwinner/終端prefixがあるため保護参照に登録し、label-free144-slot-status.jsonを別に作成した。候補freezeまでhyp/criticに渡すのはmetadataとpath/SHAのみ。旧NN0live-previewのtest名2ファイルはsealed外の各21B/0row/target0だったため原attemptを消さず `sealed-artifact-manifest.json` の保護参照へ登録した。testraw/statejournal/旧previewをlabel-freeと推測して読ませないactualallowlistを明示し、共有OS全人非閲覧や全test名artifactがsealedpathだけとは主張しない。

NN0live export previewとheap192全件export OOMは保存側の失敗として保持し、科学gameの失敗/NN不一致/棋力lossに変換しなかった。OOM後、同immutable rawをhelperheap512/CPU2/guard896MiBで再exportし、3.321377s/peakRSS582377472B/exit0・子wait。原worker192、policy/backend/Kは変更0、科学再実行0。全件QF1 export2.896601s、先行部分QF1 export2.058943s。失敗時未計測のhelper時間は0へ捏造せずhard timeoutによる上界をcost-ledgerに別記した。準備・LLM/static/Git/報告/自然監督待ちを含む受付→dataset ready calendar elapsedは2148.316s、CPU/kernel費へ読み替えない。

科学最後2026-10-04T00:01:42.075112Z、全6exit0/owned子wait/同PID-starttick不在、source runtime停止。sampled GPU-phase familyRSS最大2271436800B/guard5.5GiB、VRAM peak reserved各35651584B/6GiB、全host/瞬間peak保証0。初回admissionのparentRSS表示0はservicepath除外の限界を原receiptに保持し、既known services約158MiB+配分6GiBが親8GiB内である有限点証拠を報告した。future guardianはscheduler/monitor実RSSを明示算入、nestedtest費をrglobで計上、195への64MiB一度移転後exp有効1980MiBに厳格化した。自然監督とGPU4coreを重ねず次300s+回収窓を再admit、待ちで期限reset0。

新scope256MiB/guard224は元exp2044内、64MiB移転で有効1980MiB、未知旧保持減額/親予約追加0。必要rawは非test archiveとsealedtest archiveを分け全member SHA復元を確認し、source/config/input/全slot/失敗/費をin-memory subtree Gitで保存する。default indexは変更せず必要Git bytes復元・Beads backup後、coordinatorへ停止引渡し。195へ生成正本は速報共有済みだが、194は新NNUE学習/追加game/既default変更を自動開始しない。

保存evidence Git `8d69ed042a065afac493631d078b2d0ee2a4a9da` から非test140/sealed28の全168archive member SHAと最終datasetの必要bytesを復元確認した（Git-restore-receipt.json、1.309020s）。共有default index SHA59880a1dは不変、科学停止時source hashも一致。最初の全scope Git保存99.002331sはproduction費と別計上。保存境界の追記と最終receiptは後続小commitで特定する。
