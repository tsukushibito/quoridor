# SIGMA-ARENA-CRITIC / 試行1 / 版1

quoridor-4lc.20、critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator。目標版1/比較A継承。結論は**探索的対局no-go**。静的準備・算術の限定支持と、最終frozen runtime受入れ未完了を分ける。棋力・速度・採用の認定0。

**不支持1：応答の取引照合。** コピーしたarena.cjsのsubmitを改変せず抽出し、wireだけをmockした独立試験で、native要求generation1001に応答999999を入れてもaccepted=trueとなった。三engineとも一致generationのforeign-prefix IDを受け入れた。合法な同一Actionなら合法性検査では取り違えを排除できない。ownersと現在genだけでなく、要求に結び付く応答gen/ID/fixtureまたは取引tokenを照合すべき。browser外側genはpageで待機先へ振り分けられるため、mockのbrowser wrong-gen受理を全経路の旧応答配送実証とはしない。実NNで自然発生した誤配送ではない。証拠stage/envelope-injections.json、submit-extracted.js。

**不支持2：無応答の期限。** 同じsubmitでnative.nextを無応答にするとT10msに対し78.241493ms後もPromise未完了。runnerの90秒job停止は一要求のtimeout判定にならない。backend終了/無応答のdeadline watchdog、取消・世代無効化と後続要求の復旧規則が必要。証拠stage/no-response.json。加えて現arenaは校正/単手pilotで、game-loopは検証済みでない。

**限定支持：** 事前に読んだrawの独立算術は216=3engine×12fixture×(warm1+sample5)、36warm/180sample。g=ceil(67.900146+16.830219+0.484521+5)=91ms。T100はg>T/4で不適格。T500/1000各36要求=9warm/27sample、全72合法期限内との保存値を再計算した。両platformのscore分母へ72を二重計上しない。clock4種各12pingから区間と早側offsetを再計算。これは有限観測でtail保証なし、旧g25negativeは残る。

U64は自己prepare再生成と元JSON一致、長さ4/8/12/16各16、seed2026100201、history/turn/残plyを含むunique、golden/calibration排除。golden28/人工8と3187Action往復の自己gateを保存。真の合法200手/no-legal到達証明でなく、pool未使用・勝敗0・未知training overlap未監査。固定審判/時計/strictvalue注入の元raw読取を独立NN実行と混同しない。

**版の制限：** 静的コピーarena SHA2ba142385c84886f1ceef176127493bedac08bebed30f4dbfecb269a5b3fa0d2、game SHA dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5。最終manifestは22:35:24.644049書込停止/残PID0を記載し、最終報告SHA6e8ba5bf8665dc456bb686cdbe5f3dc404d990b0cb8187b296c35dbee605a21d。列挙sourcehashはコピー値と一致するが、全ファイル実hash照合/元入力前後不変確認は未完了。live読取算術を最終受入れへ格上げしない。最終binary/ONNX少数pilotは未実行。

**停止・逸脱：** 保守起点22:22:43、実処理期限22:37:43。自己4jobは全exit0、最終child終了22:32:48.565916、追跡starttickの現存0。context圧縮後、22:38:29.580233に最終manifest/報告を読んだため46.580233秒以上の処理期限逸脱。停止JSON保存も遅れ、全面予算遵守は不成立。再runtime0。CPU0/TID観測、RSS最大111702016B、保存約1.3MB、専用TMP/XDG、HTTP/Chrome/GPU/build/download/他者kill0。sample瞬間peak限界あり。詳細と再現command/diff/hashはCRITIC-ARENA/summary.json、arithmetic.json、各process.json、runtime-stopped.json。

**次契約への提案：** 上記取引/無応答修正、game-loopと少数最終runtime gate後のみ新契約。T500/g91は候補として再凍結。未使用poolから事前固定8prefix×先後pairをplatform別に8pair（計32game）とすれば200ply×0.5秒の上限は約53分20秒、起動/再試行余裕は別途必要。順序/seed/温度/候補hash/mを勝敗前固定。timeoutは当該engine負け、参照障害はpair無効・全pair再試行最大1回/総予算上限、複製を独立sampleにしない。固定停止・未完了は未達、score別、正式NI達成と分離する。今回の契約で対戦は開始しない。

.19の限定受入れ/過去affinity・監視・期限逸脱を保持。.20は統括受入れ待ち。深部overlay/実arena/合法200/no-legal、一般rawview/entropy/緊急reload未完了。製品standard不変、目標/他者issueは閉じない。
