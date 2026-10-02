EXPERIMENT_REPORT SIGMA-CPU-SIGMA-COMPARISON / quoridor-4lc.117 / 契約1・枠8

**登録12局を完了、候補C1.5はW6L6。全局goal終局で、644対局公開は全て合法、late／初回完成手なし／責任loss／infraunfinishedは0。** これは固定3局面・2seedの探索診断であり、正式公平性／NI／Sigma同等、係数採用、旧WDLとの統合は認定しない。actual_go=false。受領10:50:29／claim10:50:59UTC、処理12:15／新run12:10／提出12:30を維持。115は停止引渡し後に切替、再開0。

結果前登録はseed1979のinitial→asym→jump、seed2098の同順、各候補色1→2。全12起動、未開始／未完了0、RuleA最大total200ply・goal優先、正式holdout送信0。seed反復を独立標本と呼ばず、勝敗による入力選別・失敗置換はない。

| 局面 | seed1979 候補色1／2 | seed2098 候補色1／2 |
| --- | --- | --- |
| initial-p1 | W67ply／L67ply | W67ply／L67ply |
| asym-hv-p2 | L66ply／W54ply | L60ply／W64ply |
| straight-jump-p2 | W49ply／L39ply | W45ply／L39ply |

Browser mainがRuleA／合法性／時計／SAB採用／勝敗を処理し、Node毎手時計・審判・CP binding・必須事後replayは0。専用2Worker、同CPU[2]／ORT1.21.0 WASM各1thread／同固定ONNX・immutable Wasm、候補C1.5/Q0/capsと固定Sigma C1/FPU.2/temp0/原順を維持。元112の1979固定glueだけを自域adapterで登録seedへ伝播し、探索kernelは変更していない。NN障害候補loss／参照invalid、同時browser late・Judge・automation・commonidentity unfinishedの優先を小browser mockで先に確認した。

初期接続2/2合法を別分母とし、対局644と合わせ通常公開646。startupは接続6＋各pair6×6＝42NN、手NNは接続18＋対局7020＝7038、総7080。対局保存root644の648bits／137出力finite・value厳密[-1,1]／engine固有合法順／Action-P2／priorをbrowser内で確認。固定golden参照12rootと動的自己整合632rootを分け、eligible CP欠測0、priors57218。接続固定2root・startup6root/sessionは別。全深部NNや任意treeの一致は主張しない。

候補／参照の対局public中央値416.595／416.590ms、max431.850／428.625ms。初回完成publication中央値81.474／49.272ms、max177.340／89.847ms。最初のinfer入口まで中央値45.685／11.738ms、最初のsession API await中央値31.867／34.865ms、返却から完成publication中央値0.833／0.315ms。入口までの値は入力準備・root処理・schedulingと時計区間誤差を含み、未分離のfeature費を推定して差し引かない。異なる対局局面の集合なので、純backend比較や棋力因果にしない。API awaitは内核命令時刻ではない。

644手すべてpostpublic body不変。相手入力が旧ACK前386手、公開後返却棄却258、公開後に確実に開始した新NN0。自己前世代待ちmax候補0.325／参照0.075ms、残ACK重なりwall max100.870／55.080msはCPU費ではない。Worker停止区間upper<=Dは候補322/322・参照320/322、参照lower>Dは2。ACKwall max471.935／517.870msと別分類し、残処理と相手探索のCPU競合を未確認のままゼロとしない。開始／終了のclock校正と全途中rawを保存し、途中driftの連続保証はない。候補edge=sim−1/rootNNvalueと参照edge=sim/root=sim+1/rootQは別規約、参照depth/cap欠測を補完しない。

失敗は保存した。最初の接続runはNN前のprefix checkerがActionのJSON key順を同一性と誤認し停止、canonical Action比較へ修正。旧2要求未実施・NN0を保持。pair3後の外heavy検出helperが親shellのcommand文字列を誤検出し、起動列が失敗で止まらずpair4を開始した不足がある。pair4の事前admission記録欠測を遡及成功にしない。実argv判定と以後のset-eを修正、pair4自体のruntimeguard／停止証拠は保持。最終集計helperの初回opposite_previous=null例外は別CPU0 runで修正し、NN／対局再実行0。これら検査／管理例外をNN不一致や棋力lossへ変換しない。

本文前に両Modeldrop handles/activeNN0、search回収、main timer/message0、monitor callback待ち、inner forced controlledPID0とouter sole-root/subreaper同identity wait／remainingunknown0を別保存。17監視runの1231 PID/starttickは現在不在。自然終了・全期間所有保証ではない。観測currentRSS peak1,850,765,312B<5.5GiB、保存peak20,578,304B<112MiB、全heavy392.160秒<3600、各run600秒以内、観測TID affinity[2]、pure runは[0]。ru_maxrssの継承highwaterは別欄、瞬間peak／背景CPU／終了子末尾counter／初期短commandの完全CPU/RSSは未確認。既entry内配分、親保存12GiB追加0。

停止sourceはbrowser測定9eb3510（pair1）／db3bdc0（pair2〜6、追加は未使用postrun helperだけ）、offline集計8883864。必要差分と実source-binding hashを各runへ保存、共有Git default indexは変更せずprivate indexを使用。全棋譜・応答・cause flags・config・command・clock・processは各pairのGit archive正本へ保存しstream復元照合後、自域の未使用展開重複だけ整理。コード／モデルは共有参照、全履歴copy0。

詳細は[最終集計](../../research-data/ai-sigma/117-cpu-sigma-comparison/final-results.json)、[本文前停止](../../research-data/ai-sigma/117-cpu-sigma-comparison/runtime-source-stopped-before-report.json)、[必要入力・回収照合](../../research-data/ai-sigma/117-cpu-sigma-comparison/necessary-input-stop-check.json)、同ディレクトリの6pair summary／manifest／tar.gzとsetup-stop-errors。再現は新run ID／新出力で `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B tools/ai-sigma-cpu-sigma-frame8/runner.py --config <new-config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <absolute diagnose.cjs> --config <absolute new-config>`。起動は新しい許可範囲・予算を確認し、旧runへ上書きしない。

停止版をcoordinatorの受入れ／必要な独立確認へ引渡す。117は本人追加実行0、目標／他者close0。旧CPU・単Worker成績／旧失敗・期限は変更しない。Sigma同等未達・NI未立証、native未認定、deep tree／training来歴等の未確認は保持する。
