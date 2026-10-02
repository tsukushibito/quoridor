# 固定Sigma継続による中盤初手の局所品質 — quoridor-4lc.134

事前固定8rolloutは全てgoalで終わった。入力3では候補K32手を強制した枝の初手側scoreが両反復1、参照K32手の枝は両反復0だった。入力4では両初手とも両反復0だった。候補K32手だけが一貫して悪いという支持は得られず、現政策を維持する。参照の探索分布へ近づけることを改善基準にせず、この局所尺度の反復を終える。同結果からmodel/value原因を推定しない。

両プレイヤーの後続は固定Sigma C1/FPU.2/first/temp0/原合法順である。表は強制初手を選んだP2のscoreであり、候補AI対SigmaのWDLではない。原132のK32手を500ms通常候補の手とも呼ばない。

| 原132入力 | 強制初手の根拠 | 反復1/2のscore | 新公開数 | 終局totalply |
| --- | --- | --- | --- | --- |
| 3: prefix5＋新8、total13 | A161 → V(0,2)、P2 policy index112 | 1 / 1 | 50 / 50 | 64 / 64 |
| 同入力3 | B133 → H(4,6)、P2 policy index20 | 0 / 0 | 37 / 37 | 51 / 51 |
| 4: prefix5＋新16、total21 | A32 → pawn[0,-1]、P2 policy index0 | 0 / 0 | 29 / 15 | 51 / 37 |
| 同入力4 | B42 → pawn[1,0]、P2 policy index3 | 0 / 0 | 29 / 29 | 51 / 51 |

Action対応は保存CPの合法集合とブラウザRuleAの実Action/P2写像を照合した。壁や駒配置を直接変更せず、元history/side/残壁/featuresを復元し通常の1手適用でbranchを作った。入力順・枝順はpreregisterに固定した。生成prefixと敗戦線からの事後選定2位置、同seed1979・時間制限下の2反復であり、代表入力・IID・holdout・oracleではない。

入力3のA枝は同score・同終局手数でも反復棋譜が違い、第3新手の同board/historyで採用completed backup9対16、選択V(1,1)対V(1,2)を保存した。入力4のA枝も第3新手でbackup11対10、H(6,3)対H(5,3)に分かれ、goalまでの新公開数は29対15だった。B枝は各位置で反復棋譜が同一だった。完成量と選択の同時差は時間下の有限観測で、NN費用・係数・モデル価値を単独原因としない。

次判断を変える根拠は、入力3で参照K32手の継続結果が悪く、入力4でscore差が無いことにある。候補手の一貫劣化を前提にしたC/FPU変更へは進まない。後続を配分するなら、局所scoreで識別出来なかった入力/手品質尺度を再検討する。今回結果はmodel/value不良や119敗因を示さず、新実験の自動開始も行わない。

8/8開始・8goal、200ply draw0、初回無し/late/engine fault責任loss/参照NNinvalid/infra未完了/未開始はいずれも0。強制初手8はNN無し、対局新公開276と接続2は別分母で全てcompleted_legal。接続は入力3強制A後の同入力を両Workerで確認し、game入力を進めずfreshへ戻した。4job各2sessionを保持し各startup6＝計24を別課金した。手NN3148。各対局の最初の各side計16根と接続2根で648feature/137NN/finite/strictvalue/固有合法順/Actionprior/P2をブラウザ内検査した。接続の同入力両engineはfeatures exact/NN許容差内、新rootにfixedgolden参照は無い。全深部一致は認定しない。

専用Worker・モデルsession・SAB/control/世代/clockは各side独立。legacy slot名candidate＝P1、reference＝P2だが、実readyとrequest dispatchは双方固定Sigmaであり候補Wasm検索は起動しない。ブラウザmainが時計/合法性/勝敗/採用/結果を管理し、Nodeは起動監視回収と終了後保存だけを担当した。T500/cutoff402/adopt411/bounded2sampleを維持、通常採用はNN/ACK非待ち、自Worker次手だけ旧zeroを待った。NN backend故障は双方参照NNinvalid、共通browser/late/Judge/automation優先、全原因flagsを保存する。

public最大418.985ms、public前ACK非待ち199件、相手t0<旧ACK197件、旧返却discard147件。公開後新NN開始のdefinite観測0、Workerstop lower>D観測0。これらから競合ゼロ・全SAB書込402前・硬いOS期限・正式CPU公平性を認定しない。start/end clockを保存し途中drift/exactAtomicstore/内核CPUは欠測、API awaitとACKwallを純NN/CPUへ換算しない。

初期static失敗は119のfixture.playerを132のboard.turn schemaへ誤適用したglueの例外で、NN前にread-only deepCheckedStateへ修復した。初回heavy admissionは133停止SHA更新で拒否、2回目は新stop schemaのidentities欄誤読で拒否、どちらもspawn0だった。133最終4493c1d5…/71identityと元4b48794d…/65identityを区別し、管理process現物/hashと現在identity、外heavy、RAM/保存forecastを起動直前確認した。成功rolloutの再試行・結果差替え・追加game0。最初の保存CPに不要treeが含まれたpreregister草案はNN前に最小rootCPへ削減し、旧Gitと失敗を保持した。

原132 input SHA fffc171a…、source edbf29ac…、最終data/report77745c4とhandoff/reportff9ef08を分けてbindした。実装入口は6b79eca、4runのGitは各config/manifestに記載し、served adapter hashesは全job同一、原source/model/immutable Wasmは現在照合で保持している。新build/取得/GPU/係数学習/対局追加/製品統合/push0。

重175.380634秒/1800秒、管理mock0.285858秒、currentRSS peak1,678,192,640B/guard5,905,580,032B、観測保存peak34,615,296B/guard117,440,512B、affinity違反/guard停止0。CPU[2]単logical/ORT各1thread。現在保持と予約未使用分・過去peakを分け、旧未確認保持は減額しない。研究Git容量は最終保存manifestで別記する。

本文前の各job Model2drop/searchACK/timer-message/monitor callback回収とinnercontrolled/outersole-root ownedwaitを分けて保存し、管理記録556identityは現在不在だった。inner終了回収はforced receiptを含み、正常Modeldrop/検索zeroと同義にしない。現在不在を自然終了・全期間・全host停止へ変換しない。停止正本SHA bebf1bdf42bacf3e93cbc1272c28d66614a46c72f299ec431f60e38717559873。

保存は[最終集計](../../research-data/ai-sigma/134-local-move-quality/final-results.json)、[preregister](../../research-data/ai-sigma/134-local-move-quality/preregister.json)、[停止](../../research-data/ai-sigma/134-local-move-quality/runtime-source-stopped-before-report.json)、各groupのraw archive/manifest、intake失敗archiveに分け、全必要memberをstream復元照合した。元132/133/119の使用中資料を変更・削除していない。受入れはcoordinator、正式棋力/NI/Sigma同等/係数採用/actual_go/目標達成は未認定。
