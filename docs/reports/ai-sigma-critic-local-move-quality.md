# SIGMA-LOCAL-MOVE-SAVED-INDEPENDENT / quoridor-4lc.135

契約1・枠9。**原134の局所後続得点・8棋譜・276合法公開を有限支持。候補だけが悪い手を選ぶという解釈はこの2入力では支持されない。** 候補AI勝率、真の最適手、C/FPU因果、正式公平性・NI/Sigma同等・係数採用は未認定、actual_go=false。

本人受領2026-10-02T17:09:42.015555696Z、ready/show goal+self・pauseなし・担当確認後135のみclaim、統括開始report accepted。処理17:39:42/newcommand17:34:42/提出17:49:42。133のsource/NN停止後の自己新scope。CPU4/RAM8GiB/12GiB・親枠9終了23:20:59・既critic128MiB/combined112MiBと配分を維持した。原134/132/モデル/共有sourceは書込0。

初期134停止SHA `bebf1bdf42bacf3e93cbc1272c28d66614a46c72f299ec431f60e38717559873` と後着最終停止SHA `656a9265724f57c07207c50261038e4d881e01db1e43ff2f7da17c368c76aa0c` を区別。最終data/report Git `7af16352efc00e56101fb9432ea5698473decec3`、handoff Git `bd339e21af2cf1a60d2715506d4aebe5fd1dd01b`、handoff SHA `4335e4d86c5e840da6c8b1a369555e4572e1be9dd1d6e541367e053562afe9da` の必要4fileは現物/Gitblob一致。4run測定Gitは6b79eca/64a656a/b7f4db3/857ce64を別に記録した。原132固定入力SHA fffc171a…f56b01一致。指定preregister SHA a3b368…e666a38は初期Git9c8224aへ照合し、実測355d9064…1289dとの差は非root CP tree除去と注記のみ。登録順・条件・強制Action・fixture・rootCP不変を独自比較した。

ブラウザ内自己checkerは登録8全棋譜のprefix/history/key/手番・壁残数、強制P2 Action161/133・32/42、各公開の合法性・採用sequence/Action・UTF8 body不変・goalと得点を再算した。Labelや原owner集計のコピーではない。以後の両slotは固定Sigma C1/FPU.2/first/temp0/originalorderであり、candidateというslot名も参照policyを実行する。必要5served script実hashが全4run保存bindingと一致、adapter測定Git一致。実producer dispatchをNN0 stubで両slot→runReferenceと確認し、browser内で両slot NN failure→reference_NN_invalid/unfinished、late/Judge/abort共通原因優先を必要枝だけ確認した。

| 入力 | 強制P2 Action | 2反復のP2得点 | 新公開数 | goal totalply |
| --- | --- | --- | --- | --- |
| 3 A | 161 | 1, 1 | 50, 50 | 64, 64 |
| 3 B | 133 | 0, 0 | 37, 37 | 51, 51 |
| 4 A | 32 | 0, 0 | 29, 15 | 51, 37 |
| 4 B | 42 | 0, 0 | 29, 29 | 51, 51 |

全8goal、draw/責任loss/infraunfinished/未開始0。prefix13又は21＋強制1＋今回新公開をtotalplyと照合した。強制一手のNN=0、新公開276全合法。接続2要求は別で手NN9/10、対局手NN3129、接続込み3148、startup4job×6=24別。discardは対局145/接続込み147、public before ACKは対局197/接続込み199。相手t0<旧ACKは対局内197。自己Worker旧zero後t0・自待ち、同世代body不変・旧返却棄却を別に確認した。

全276公開の最終stamp/予定adopt411・cutoff402・D500、旧ACK/API開始をclock誤差区間で独自算術した。最大公開418.985107ms、最大timer予定遅れ7.925049ms。Worker停止upper≤D276、lower>D/境界跨ぎ0、ACKwall>500 0。確実/可能な公開後新API開始0/0、402後0/0。開始・終了校正の区間算術は一致したが途中driftは未観測。Worker停止・ACKwall/APIawaitは有効思考CPU・内核時刻・硬いOS締切・実効資源公平性を証明しない。

読取前に各rollout最初の保存root計8を選定。648features・137NN shape/finite/strict value[-1,1]、実fixedSigmaの合法Action順・Action別softmax prior・reference edge=sim/root=sim+1をbrowser内自己算術で確認した。全8rootは強制P2の次手P1であり、P2の新NN数値一致を認定していない。P2 Action変換は強制入力と全P2公開の合法replayで確認した。固定中盤golden0、動的自己整合であり全深部一般NN一致ではない。共有RuleA/特徴・Action変換ロジックの独立性限界を保持する。

入力3 Aは両反復score1/終局64でも、第3新手の同key/historyからcompleted backup9/16、Action154/162に分岐する。入力4 Aも第3新手で同入力backup11/10・Action111/110に分岐し、goal ply51/37。Bの2入力は各反復の全公開Action軌跡一致。これらは時間下completed量・選択の有限な反復揺れであり、同結果を完全再現としない。model/value原因も自動推定しない。

評価設計では、この尺度は「この強制手を選び、その後を両fixedSigmaに任せた時の局所得点」に答える。入力3ではAがBより良い有限後続例、入力4では両方P2負けで差を区別しない。事後の敗戦線2位置、同seed/temp0/first、固定後続policy依存なので8独立棋力標本・最適手oracle・単因子効果にはならない。現在の尺度を同条件で反復し続けても実装選定への情報増加は乏しく、今回の反復終了は妥当。ただし局所差の観測自体を無価値とはしない。

最大1つの安い次案: 既保存の第3新手で、同入力のSAB完成backupを共通帯に合わせてAction推移を比較するNN0解析。共通backupで一致すれば時間下の完成量の揺れを優先観測、不一致なら状態/規則bindingを先に調べる。追加対局なしで交絡を絞れるが、長期手品質や棋力の証明にはならない。今回実行・新配分0、採否はcoordinator。

起動直前admissionはsource134停止/current556identity不在・外heavy0・RAM/保存headroom・自己旧remaining/unknown空を成功確認し、同必須分岐内でchild spawn前に実行した。false/unknown/readerror/deadlineは例外でPopenへ進まない。136CPU0静的に新承認gateを設けていない。純保存browser run17:17:00.946897→17:17:08.175869Z、7.228972秒、currentRSS peak1,282,445,312B<5.5GiB、保存peak9,150,464B<28MiB、全観測TID CPU[2]。新Model/session/AIWorker/NN/search/game/holdout/build/取得/GPU0。Nodeは起動/外監視・回収/終了保存のみ。開始時critic artifact現在量85,872,640B＋forecast4MiBはcombined112MiB内、予約追加0、未確認旧保持減額0。瞬間peak/短い初期読取・closure PIDRSS/全期間affinityは未保証。

自己不具合は保存した。初期preregister hashの版混同をGit差分確認で訂正。browser adapter生成ValueError、その後の最初管理runはbrowser.cjs欠落でexit1/Chrome未開始。r2は独立解析成功、科学結果を選別していない。継承browser-summaryのone-pair表記とadmission返却pathの変数shadowingは記録欄だけ修正し、元run/sourcehashとerrataを保持、新Chrome再実行0。元134のadmission2失敗spawn0・静的schema失敗・packed Git課金helper失敗も保持し、NN不一致や棋力lossへ変換しない。

本文前自己3管理job44identity現在不在、inner browser grace未完了forced=true/owned回収、outer同identitywait/adoption2/remainingunknown空、monitor callback停止を分離して保存した。自己新Modelは0であり原134各4jobのModel2/search/main/monitor停止は原保存receiptとして別確認。現在不在は自然終了・全期間保証ではない。必要入力hashafter一致、自己使用終了後のcompact展開だけ整理、原データ削除0。

再現: 自域prepare.pyが必要archive memberのhashを照合・compact JSON化し、結果前selection/configを保存。`python3 tools/ai-sigma-local-move-independent/runner.py --config <自己config> node --max-old-space-size=192 <自己browser.cjs> --config <自己config>`。必要command/UTC/monotonic/Git/PIDstarttick/全失敗・資源・復元は自己dataへ。最終入口の記録欄訂正はmetadata-errata.json、測定時sourceは各run.inputs.jsonを参照する。

[独立算術](../../research-data/ai-sigma/135-local-move-independent/all-independent.json)・[最終入力binding](../../research-data/ai-sigma/135-local-move-independent/final-input-binding.json)・[自己停止](../../research-data/ai-sigma/135-local-move-independent/runtime-source-stopped-before-report.json)・[全失敗](../../research-data/ai-sigma/135-local-move-independent/failures.json)・[archive復元](../../research-data/ai-sigma/135-local-move-independent/archive-manifest.json)。受入れcoordinator、goal/他者close0。
