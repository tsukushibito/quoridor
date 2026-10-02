# SIGMA-C-FACTOR-INDEPENDENT / quoridor-4lc.111 / 契約1・枠7

**Cだけの有限探索感度を支持する。係数採用・棋力改善／悪化・正式NI・Sigma同等は未判定。** 指定の独立4検索は全てK32へ到達し、原asym／jumpの訪問・Action差を再現した。原4局のW0L4もブラウザ内保存replayで確認したが、普遍的C悪化とはしない。新対局・holdout・build／取得0、112の新2Worker条件は混合0。

受領08:33:31UTC、全文／現行枠7／common／critic／記録規約、ready/show・pauseなし・本人担当を確認して111だけclaimし開始報告accepted。処理09:18／新run09:13／提出09:28を維持。原tested Git0f0597e73e5444c2a576121242a02e18417aad01、停止SHAbd2029a9…ab9263、最終data Git99436415e08f52f1232c6a92766c8a2dc78ee7b9を固定。必要source17とGit／current一致、差は`PUCT_C:1.5→1.0`一行。Cargo manifest／lock／lib／researchは同bytes、保存toolchain1.98.1／release-offline-locked flagsを確認した。baseline292139Bは既immutable SHA1f54d0…78a01とbytes一致、C1 292135B SHA8438310c…2d9dd。新compile0。分類・監視stop callbackの共通修正はC因子と別に扱った。原build1のmodule不足、build2の共有targetによる誤再利用、別target build3を区別した。

原6行は全てsim／実rootN32、edge和31、NN32、terminal-noNN0／cap0。192backupには最初baselineのinner登録回収エラーexit1を含め、Modelzero／outer回収成功でinner成功へ置換しない。原K8 original/rebuilt3局面はブラウザ内の独自照合でCP完全一致・648bits一致・137NN混合gateを確認し、追加K8実NNは0。

| 独立K32比較 | baseline→C1 Action | 訪問差辺数 | TV | depth |
| --- | --- | ---: | ---: | --- |
| asym-hv-p2 | 67→67 | 2 | 2/31 | 7→6 |
| straight-jump-p2 | 31→131 | 3 | 7/31 | 5→3 |

固定順asym baseline→C1、jump C1→baseline、seed1979／Q0／sqrt(N+1)／tie・finish・order／512node・depth24を保持。各検索で新handle／contextを生成し、木・history・cache持込0。独立は4検索／128NN、3session startup18は別分母。初期は保存のみで訪問同／Action13を確認したが、root edge value和は6.186480→6.201153で、訪問同をvalue／全探索同一とは呼ばない。entropy／TV／全step backup数・直接rootN・NNcallsは独自ブラウザ算術で確認した。等completed比較を500ms比較や純NN費用比へ変換しない。

独立4 rootの648bits×4／137NN×4／合法prior510はshape・finite・strict[-1,1]・P2・engine固有順／Action別softmaxを先検査し、固定abs1e-4＋rtol1e-4を通過。最大NN差3.576279e−6、prior差3.417633e−7。保存公開rootは必要11sampleで固定参照8／動的自己整合3、うちCP欠測1はpriorを捏造0。動的自己整合から一般NN一致／深部安全性を認定しない。

原4局はgoal loss3＋初回eligibleCP無し責任loss1、291公開＝290合法＋null1、late／infra未完了0。手NNは対局589＋630＝1219で、課題全体検索1469／startup54／総1523と区別する。色2・total ply71のnull（request138）はroot準備236.810ms、API await110.560ms、初回受信のNode換算区間434.415–434.625ms>402、採用417.420ms。root NNはfiniteだがeligibleCP／prior欠測であり、NN不一致やC普遍悪化の反証ではない。RuleAを共有する合法replayの独立性限界を保持する。

開始・終了8pingをブラウザ内再算し、その観測endpoint envelopeでも原C1対局Worker停止upper<=500が286／lower>500が5、ACKwall超過5。baseline小public2はWorker超過1／ACK遅1、内部APIの確実402後・公開後1を確認し、旧107のAPI0を継承しない。公開最大は対局447.760ms、ACKwall最大557.645ms。次t0>=前ownedzero受信、Judge／clone／必要UTF8後stamp・公開Action不変を確認。endpointだけで連続drift／硬い期限を保証せず、API awaitを内核命令時刻、ACKwallをCPU時間としない。

同時sharedFAULT＋late／Judge／cancel／abortを含む8caseを実classifyResponseへ注入し、原因flags保持・不明sharedFAULTはunfinishedを確認した。原109や旧ゲームを新分類で再分類0。Nodeは起動／監視／終了後保存のみで、保存棋譜／時計／数値／C分布の判定は全てブラウザ内。公共の最初のCPを得る費用が500ms内に収まらない条件は設計上の不足であり、C感度だけでは解消したと判定しない。

本文前停止を保存し統括へ速報accepted。NN最後08:48:41.970、全Chrome最後08:53:22.620。count zero4・3 Modeldrop handles／activeNN0、main timer／message0、監視callback待ち、inner forced controlledPID0とouter同identity wait／remainingunknown0を別確認。自己208 identity現在不在は自然終了／全期間保証ではない。管理heavy4run計53.386秒、観測全TID CPU2／threads1、current RSS最大1,580,060,672B<3.5GiB、保存peak11,276,288B<28MiB。準備runs親dir欠落はchild／NN／検索0で保存し自域を修正、producer変更0。40ms瞬間peak・終了子CPU・背景負荷・初期短静的commandの資源欠測を保持。archive込み自己約12MB、既critic128MiB／combined112MiB内追加予約0。default Git indexは変更せず専用indexを使用した。

[詳細算術・全分母](../../research-data/ai-sigma/111-c-factor-independent/independent-summary.json)、[停止](../../research-data/ai-sigma/111-c-factor-independent/runtime-source-stopped-before-report.json)、[source/build根拠](../../research-data/ai-sigma/111-c-factor-independent/source-build-proof.json)、[必要証拠](../../research-data/ai-sigma/111-c-factor-independent/111-run-evidence.tar.gz)、[復元manifest](../../research-data/ai-sigma/111-c-factor-independent/archive-manifest.json)。自己archive SHAfc7014cb871198fc00acc9e2bf7d845b07e4eec9060dd4b4d6b03c914e6cb89d、915419B／132member復元一致。原archive SHAb22feaad…a5b4dの必要23入力と初期参照／afterhash一致、全296member復元はowner結果と区別した。

primary checker Git54c2d89003c4e21633c9d78986d35b5781abbcfa、NN0時計checker8381563。再現は現在の許可と新configで`UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 SIGMA77_GIT_COMMIT=<版> python3 -B tools/ai-sigma-c-factor-independent/runner.py --config <絶対config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <絶対driver.cjs> --config <絶対config>`。原500ms対局の新NN再実行0。停止→研究Git保存／復元→backup/report後idle、111受入れ待ち・goal／他者close0。旧成績・失敗・NI未立証／Sigma未達とtrue合法200／no-legal、rawview／entropy／training来歴の未確認は保持する。
