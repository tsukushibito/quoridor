# SIGMA-POLICY-FACTOR-CHOICE / quoridor-4lc.136

**現政策を維持し、次は係数の一括変更より同政策の完成量・費用境界を優先する。** 保存の対応局面で共通backup1〜9の公開Actionが9/9一致した。FPUだけを変える案も残すが、参照分布への接近を改善としない。静的有限支持であり、NN/Chrome/model-load/探索/対局/build/取得/委譲0、actual_go=false、係数採用・棋力/NI/Sigma認定0。

本人受領・claim2026-10-02T17:10:11.284075Z、ready/show goal+self・担当/pauseなし確認。処理17:40:11.284075、新command17:37:11.284075、提出17:50:11.284075。親枠9/CPU4/RAM8GiB/保持＋予約12GiB・終了23:20:59を維持。134最終保存や135裁定を開始gateにしていない。

判別する不確実性は、未訪問Q0が配分を広げる効果、finishが局所的に良い手を保つ効果、同wall内の完成量が手を変える費用原因である。119有限弱さをC/FPU/準備費一つへ帰属させない。現政策維持には、134入力3で候補由来の強制手が固定Sigma由来より良い有限後続結果、入力4は双方負け、123/125・126の方向混在という根拠がある。局所尺度の同条件追加反復は終了する。

読取前に132入力3/4 A/B初期根4、134入力3A rep1/rep2第3新手根2、入力4rep1A/Bの最初の異Action対応根最大2を固定した。入力4は両29行のidentity/key/history/prefix照合で対応異Action状態がなく、予定2根は欠測・補充0。実根読取は計6。全棋譜replay/全root解析は行っていない。

| 保存位置 | A | B又は反復 | 意味 |
| --- | --- | --- | --- |
| 132入力3、K32 | Action161、訪問20/107 | Action133、訪問3/107 | 根特徴・NN一致、政策は束で異なる |
| 132入力4、K32 | Action32、訪問29/94 | Action42、訪問5/94 | 同上、134では両枝得点0 |
| 134入力3A第3新手、同入力 | backup/NN9、Action154 | backup/NN16、Action162 | 両slotの実policyは固定Sigma |

132の4根はbackup32/NN32/terminal-noNN0、edge和31。候補rootN32はsource条件、参照root_visits32はrawを区別した。候補edge value_sumは親視点、参照保存col3はchild valueSumで親Qにするには符号反転する。P2の161/133はcanonical policy112/20、32/42は0/3。receiverの手の再選択はしていない。

原finishは6/6一致。入力3候補は161と133が各6訪問、prior .343202/.225944で161を採る。同候補順のfinishを先頭優先へ仮想変更すると133になるが、134の固定Sigma後続では161枝score[1,1]、133枝[0,0]。したがってこのfinish変更はこの局所出口では逆方向である。入力4の先頭優先対照は32のまま。C1.5→1のf32転記による仮想次selectは入力3 Action144、入力4 Action196で各不変。Rust全bits検証・変更後全探索・C効果ゼロという主張ではない。

候補の訪問済み親Qは入力3全20/20・入力4全29/29が負、未訪問Qは0。参照より広い訪問と整合するが、C/N/order/精度/深部差も競合する。候補の実parent meanは保存欠測で、edge平均や参照meanで補完していない。実reference-coreのbestChildを人工2根でNN0実行した。C1.5を与え、nodeN11/visited child10・同prior/Qでも初期root評価−1/+1によりFPU選択3/5、Q0選択は両5だった。FPUは実parent meanと訪問済みbasePrior和に依存し、係数名だけで候補への方向を予測できない。人工probeは候補実FPU/棋力実績ではない。

134の第3新手2根はkey/history/prefix/model/limits・保存根NNが一致。共通completed1〜9のSAB Actionは9/9一致し、K8/9で両154、rep2の最終K16は162。量と公開手の関係を有限に絞れたが、全K/deep NN/CPU一致を証明しない。後続は両固定Sigmaでありcandidateという物理slot名をRust候補policyと誤認しない。numeric_selected=falseはownerの初回選定gate外という意味で、今回読んだraw根NNが無い意味ではない。

全8compact winnerとforced_sideから得点を別算術し、134集計と一致、新公開276と接続2を分けた。startup24/手NN3148も別。135後着独立保存replayは8goal/276合法と同局所解釈を支持しているが、135のcoordinator受入れを先取りしない。入力3A同score1でも軌跡不同、入力4両0は尺度が差を識別しない例であり、一般最適手/model原因を断定しない。

次案は[proposals-v2.json](../../research-data/ai-sigma/136-policy-factor-choice/proposals-v2.json)。先行案v1も保持する。

1. **P2・計測対象変更を優先。** 同じ134入力3A第3新手1状態、固定Sigma政策/T500を保ち、warm1/sample3最大4要求で時刻別CP、準備・API・返却棄却・残CPU・threadCPUを分離する。共通KのAction/数値が一致し費用境界が違えば、その境界だけ次修復へ。共通Kで不同なら最初のstate/order/NN差へ変更、量安定/欠測ならこの枝停止。writer experiment15分＋CPU2/thread1/RAM6GiB runtime≤60秒＋必要独立保存10分、build0。計測費・OS・1事後状態が交絡し、APIawaitやsameKを純NN/同CPUとしない。新実行は後続配分のみ。
2. **P1・未訪問FPUのみの対照。** 候補Q0→実node valueSum/visits−.2sqrt(visited basePrior和)、C1.5/√(N+1)/f32/order/seed/finish/caps/backend/modelは固定。両variantに同じ直接node valueSum記録を追加し、baselineが変わらない小parityを確認する。登録132入力3/4×両variant K32＝4検索、最大128手NN＋startup6。Action不変・訪問だけの差なら採用0、入力3が133へ変われば既局所出口では悪化方向なので政策維持、他の新手は別品質評価へ。writer experiment35分＋次配分のcached build≤120秒＋runtime≤60秒/CPU2/RAM6GiB＋独立保存10分。parentQ欠測/実装bugは未成立。集中を改善としない。

131/133の非自明な有限深さoracleは将来の別品質尺度として競合するが、未解決なら自動拡大しない。正式NI/均衡校正/全fault/全役承認を診断の一律入口に追加しない。両案とも固定Sigma正式参照を置換せず、今回実装/NN/対局許可は発行しない。

134最終data/report Git7af16352…、handoff/storage Gitbd339e21…、handoff SHA4335e4d8…/stop656a9265…/final-resultsc4b7dae0…へbindした。初期preregister a3b368…と実行前355d9064…を保持し、重複tree省略のみという統括裁定を条件変更へ変換しない。必要current source参照と保存archive afterhashを区別し、全履歴/全source再hashはしていない。

管理5run、最初のhistory配列順assertがexit1、map同値照合へ修復後exit0×4。検査器失敗を入力/NN不一致やlossにしない。20ms観測RSS最大90,570,752B、全観測TID CPU0、管理wall計.9594秒、guard0。本文前17:30:30UTCに自己10PID/starttick現在不在・外側wait完了とsource停止を固定。停止時自己allocated225,280B＋旧保守保持8,073,216B＝8,298,496B、combined14MiB/既予約16MiB内、追加予約0。旧値は保守provisionで全owner現在量証明ではない。短命command/瞬間peak/副次CPU/Beads量・現在不在と自然/全期間保証の差を保持する。

再現は`python3 tools/ai-sigma-policy-factor-choice/supervise.py <new-run> python3 tools/ai-sigma-policy-factor-choice/check.py`、人工probeはNodeheap192でprobe.cjs。自己run設定・command/sourcehash・失敗・必要入力・停止は[保存data](../../research-data/ai-sigma/136-policy-factor-choice/)へ。元134/132/model/source/製品/default index書込0。自己Git固定・backup/report後coordinator受入れ待ち、goal/他者close0。
