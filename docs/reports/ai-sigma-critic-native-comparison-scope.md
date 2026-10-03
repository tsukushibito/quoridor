# 166：native比較の参照・時計・費用の有限裁定

2026-10-03、critic。契約Git `d0136c1293dc66be2d165d5c012a40b898655f23`、親版11。受領04:38:32UTC、本人claim04:38:55UTC、直後に静的開始をcoordinatorへ配送。処理期限05:03:32、新command期限05:00:32、提出期限05:13:32。165への実装開始gateは追加しない。

第一選択の **private Rust native faithful MCTS 対 固定Sigma-Web751186をnative-hosted JSで実行し、双方が同じONNX・常駐Python native CPU providerを使う経路** を支持する。これは移植基準と教師生成・評価費を確かめる比較である。Sigma C++ nativeとの比較でも、ブラウザ上のSigmaとの正式NIでもない。151/153/155の有限機構・合法性を再利用し、新native provider・輸送・時計の差だけを必要範囲で確認する。現時点でnative NI、browser NI、NNUE最高棋力はいずれも未認定。

## 最大1案：共通event-driven回収を伴うnative診断

双方に同じcontroller monotonic時計で、入力供給可能なactual t0から合法な応答の受信・検査・public採用まで最大500msを与える。特徴生成、検索、NN IPC、Rust操作pipe、JSON変換、receiver検査を内側へ含める。モデルload/warmupと、採用後の原因側cleanupは別に記録する。期限後に返ったNNは採用済CPや次検索へbackupしない。双方の旧検索・NN要求・reply待ちが回収されたquiescent状態から次の入力actual t0を置く。受付時刻だけでquiescence成立とはしない。

この別測定modeでは次t0が旧処理回収を待つ。通常browserの「相手t0は旧ACK非前提」を遡及変更するものではない。固定1000ms周期は不要で、回収が短ければ固定idleを払わず進める。残処理が長ければその費用を原因engineのcleanupとして総費に足し、相手の500msを削らない。API awaitやACK wallはkernel CPU時間ではない。同じwall上限・同じ割当logical CPUによる診断を支持できても、未測のkernel CPUの完全同値は主張できない。

最小記録はrequest/engine/世代、controllerのt0・deadline・CP受信開始/検査終了/public、root completed数、first completed CP、NN start/return/discard、retire開始/回収終了、次t0、provider/session/割当でよい。相手のPython perf_counterはelapsed副証拠、Rust Instantはduration副証拠とする。時計の名前がmonotonicというだけで別processの絶対epochを接続しない。controllerの時計で締切を裁定できない場合はCLOCK_UNSETTLED/infra unknownで、棋力敗北を捏造しない。

初根のNN完了前にpublic期限へ達した場合、完成済CPがない事実を記録する。rootを必ず一回完了させてからt0を置くと最も高価な最初の評価を無料化するため、firstCPは内側へ含める。fallback・候補fault・参照fault・未開始・未完了・共通infraを結果前に定義する。候補faultの運用score0と、双方正常terminalの品質scoreを別にし、参照faultを自動的な候補勝ちにしない。

## 独立指摘と静的反映

原保存 `mcts_worker.original.js` のSHAは130 source bindingの `f2de9444…cfe8fa` と一致した。原runMCTSはroot展開/backupをloop外で行い、進捗は最大約40回で、root/毎simulationにsetTimeoutはない。一方、browser研究reference-coreにはrootと各simulationのtimer yieldが入っていた。これをNodeへそのまま持ち込んでRust側に相当の待ちがなければ、sameK一致でもsamewallは研究adapterの非対称を含む。探索係数・FPU・mean・合法順を変えず、native用共通制御と実輸送費を事前固定する必要がある。timer除去だけを棋力改善やNN差へ変換しない。

04:49:44UTCの165 private source snapshotでは `reference-core-native.js` のrunMCTSから人工timerが除かれ、`common.cjs` の時計はNode hrtime、`ort.py` のPython時計は「not controller epoch」と明記されていた。ort.pyはCPUExecutionProvider、intra/inter1、ORT_SEQUENTIAL、648個f32 bit入力、137個f32 bit出力を構成し、session情報を返す。**この局所source反映は支持するが、arenaの共通制御・締切・回収が実成立した証明ではない。** coordinatorによる採択/配送と科学反映も別である。ownerの事前登録と有限実測で対応を確認する。

ORTのintra-op設定とexecution modeは実行条件の別項目であり、スレッド設定を省略するとCPU core数に応じた既定並列が生じ得る。実session version/provider/optionsとowned affinityを保存する必要がある。[ORT公式threading資料](https://onnxruntime.ai/docs/performance/tune-performance/threading.html)。今回確認したのはsource設定であり、新sessionやNNは実行していない。ORT1.30 native CPUと旧ORT1.21 WASMは同じ重みでも別backendで、数値一致の実測は165の担当範囲である。

StageAの5入力×両engine K32で、history/side/features648/f32出力、Action順・選択path・訪問・finishを有限照合する。root32/edge31と手NN320、startupを分離する。旧WASMとのabs/rtol1e-4比較と、同native backendでの離散一致を別にし、微小prior差の許容でpath/訪問/Action差を救済しない。全deep、全root、全履歴hashを新gateにしない。

## openingと主問いの限界

提案8pairのL12/13/24/25、短合法opening、BFS双方距離≥3・差≤1・残壁≥2は、旧4/5/12/13より対象を変える診断分布であり、均衡を証明しない。BFS距離は駒跳び・将来壁・代替路・手番の価値を表さない。旧155の同盤面側winner7/8のように、局面側の優位が両色結果を支配するとpair score .5は大きなengine差も隠し得る。今回の16局は合法運用・同wall完成量・費用を見つけるには有用だが、棋力差への感度や代表性は未成立である。

予定16分母、8pair Xi、色/層、同盤面側winner、両色候補敗、未知を全部報告し、支配的なpairを結果後に除外しない。重複は登録どおり保持・識別し、16独立位置と数えない。固定PRNGや共通searchseedだけでIIDは証明されない。正式native評価では独立抽出規則・開始分布とsampling仮定を新データ前に定める。今回opening/教師行を正式holdoutへ流用しない。追加のopening選定案はここでは提出しない。

## 費用と正式計画への接続

総費はinit/warm + 各turnのpublic−t0 + 原因側cleanup + 入力前審判/記録/保存で計上する。内側NN awaitと、その内側API/輸送内訳を二重加算しない。JS側NN pipeに加えRust操作pipeがある非対称は、native実装全体の性能比較には含まれるが、MCTSアルゴリズムの因果効果とは分ける。firstCP、steady NN、輸送、rule、completed root、games/secと有効教師行/secを並記すれば、次配分を推論・輸送・探索のどこへ向けるか判断できる。固定batch1の8要求を真batch8と呼ばず、GPU provider文字列の存在を実GPU実行へ格上げしない。

165の16局は200ply×500msで思考だけ最大1600秒。1800秒の対局予算にはload/cleanup/saveも必要なので、上限到達時の未完了はunknownである。仮に将来publicを毎手500ms固定とし、旧診断平均53.5625手だけを費用例へ借りると、1200局は32137.5秒（8h55m37.5s）単独、2arenaで速度維持なら4h27m48.75s。最大200plyなら33h20m単独。これは新native実費や並列倍率の実測ではない。早い合法publicを認めるmax500方式なら費用が変わり、owner登録を先に固定する。旧browser411ms由来の7h22m21sや4arena倍率をそのままnativeへ転用しない。初期single arenaの最大2logicalを4arenaへ自動拡大しない。

将来正式native版は候補binary/source、fixed Web751186、ONNX d790dac、provider/version/options、時計・課金/隔離mode、開始分布、fault全予定分母、固定m/停止/再試行を結果前に別登録する。5pp/片側95%の第一方式 `L=max(0,mean−sqrt(log20/(2m)))>.45` は条件付きに継承できる。m600で平均.5が通過境界を満たすことと高powerは違う（158のIID Bernoulli pair例約.51628、真平均.5で分布自由95%power十分m2397）。旧browser計画・8pair・rawは変更/合算しない。予定未知score[0,1]によるlow/high meanを主分母へ残し、complete-onlyは補助にする。正式版manifest・sampling・時計/実効費・modeの根拠が揃うまではformal_ready=false。小診断の開始条件へ正式全保証を持ち込まない。

## 実行・保存・停止

自域のみ編集。再現commandは `taskset -c 0 timeout 60s python3 tools/ai-sigma-native-comparison-scope/static-scope.py`。静的run1はsource7点のsnapshot SHA、原版hash、native loop人工timer不在、provider設定文字列、費用算術を確認した。NN0/modelsession0/Chrome0/build0/game0/train0/GPU0/取得0/委譲0。自己peak RSS14,962,688B、CPU0単1。実輸送・source実行・実NN・kernel CPU・quiescence・formal NIは検査していない。一次資料のNode24 timerページ取得はInternal Errorで、その内容を結果根拠に使っていない。

保持は既旧未知88,190,086Bを減額せず、158 current361,975B、161 current434,616B、新forecast2MiBを含めcritic112MiB guard内。全原archive/rawコピーなし。必要sourceはhash参照、自己run/通知/不足/停止/Git stream復元とbackupは166の保存記録に対応する。自己科学childは作成せず、静的runはexit0、source編集は最終保存後停止してcoordinator受入れへ引き渡す。通信受理を科学成立にしない。
