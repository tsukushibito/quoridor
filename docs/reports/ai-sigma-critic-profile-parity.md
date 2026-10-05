# SIGMA-PROFILE-PARITY-CRITIC 独立検証

Beads: 目標quoridor-4lc / 自子quoridor-4lc.8 / 試行1 / 契約版1。
critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。
目標契約docs/design/ai-sigma-research-goal.md版1、AGENTS/common/critic/team design/AI設計§8/14.4/14.5/storage/handoffを継承。今回受入れは検証方法・証拠のみ、棋力/速度達成ではない。

## 判別した問い / 結論

**支持・限定可**: 最終coarseのExpand祖先記録、Legal内BFSを含む和集合の排他的集計、全rawの決定的出力一致、原runの事前5% gate通過を独立読取・算術で確認。参照側28fixtureは自己copyから2回同bytesを再生成し、合法20/人工8の分類、schema、136↔209写像とP2特徴を独立照合した。

**保留・追加検証必要**: 計測器の低歪みについて全面可とはしない。統括short replayのwalled-midgameは+5.131%で固定5% gateを超える。そのrunの低歪み主分類は保留。H1不支持・最適化失敗という意味ではない。Rust/NN内部parity、Wasm全探索wall、正式無競合比較、速度/棋力改善、モデル配布可は未確認。

## 実施内容 / 基準入力

作業場所/workspaces/quoridor/.worktree/ai-sigma、codex/ai-sigma、入力HEAD1482df8da6dd91c95db211aeaa914af775b2bc76。HEADだけで未コミット内容を確定しない。原.5 final-source/とfinal-source-hashes.jsonを正本とし、snapshotに存在する全ファイルをmanifest照合。現在.7が変更するsourceは検証入力にしない。読取時のlive差はposition.rs、phase3-performance.spec.ts、ai-sigma-runner.pyにあり、両hashをresources-shutdown.jsonに保存した。並行変更を元runへ混入しない。

入力reportのSHA256:
- experiment-profile: be856e7727e129931d46bf0a8bef9dff836608583bde9a8d016994261329b044
- hypothesis-parity: 3f2a7ccce82552bca670b3e518fda84953f15421623504ceef9d34a9d6143460
- 旧critic比較: 607618c36454a18bb4f9ba2ec954b074a58e82214648e7991f5030b8400c74cf

全読取payload、final-source、契約2/統括raw、manifest、launch、初期2報告、lockの実hash/sizeは[before](../../.artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/input-hashes-before.json)と[after](../../.artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/input-hashes-after.json)。207ファイルは検証前後で不変。原artifactへ書込み0。binaryもmanifestと実SHA256一致（実行0）、[資源/終了記録](../../.artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/resources-shutdown.json)に保存。

## 問い1: profilingの独立照合

final-source/core/profiling.rsのFrame.in_expandはExpand自身、または直上frameから祖先flagを継承する。metrics_in_expandはこのflagで直接記録し、Evaluate→Transition→Distanceを展開内/外に区別する。Drop時exclusive=inclusive−直下timed child inclusive、親へ子inclusiveを一度だけ加算。coarseでparent=LegalのDistanceはstart=None、counterもなし、時間はLegal self内に残る。Legal外Distanceは時計あり。coarseのLegal内Distance count0は未計測であり呼出しなしではない。LegalとDistanceのexclusive和でBFSを二重加算しない。clock bookkeepingもselfに混入し、allocator時間とは区別不能。

AI lib expand()のRAII spanは評価まで継続する一方、simulateのdepth/node cap→safe_valueはExpandの外。別test sourceではEvaluate/Searchの祖先側count0をassertする。今回cap testを実行しておらず、全通常raw cap0だけからcap枝runtimeを確認したとは言わない。arena capはexpand中にも発生するため、cap全種類を機械的に「外」とする分類も不適切。

独立verify.pyは原契約2の全126child rawと統括24child rawを読み、warmup含む全sampleで合法ID順、距離、全合法遷移、選択Action、全stats、root edge action/prior/visits/value_sum bitsを比較。各集合内・両run間で一致。Search exclusive和=Search inclusive、Expand祖先exclusive和=Expand inclusiveも各warmup/測定sampleで保存則を確認。独立算術は元native-summaryと一致。

R_exp=Expand祖先付きLegal/Distance exclusive和÷Expand inclusive。R_all=同カテゴリの全検索exclusive和÷Search inclusive。f_expand=Expand inclusive÷Search inclusive。下表は合算nsの比（平均割合とは区別）、overheadは全warm sampleのmedian対元control。統括列は別窓/別標本の再集計。

| case | R_exp | R_all | f_expand | 原run overhead | 統括short overhead |
| --- | ---: | ---: | ---: | ---: | ---: |
| initial | 98.854% | 98.210% | 98.756% | +2.269% | +4.024% |
| opening | 99.010% | 98.345% | 98.754% | +1.681% | +3.288% |
| walled-midgame | 98.946% | 98.349% | 98.564% | -0.960% | +5.131% |
| p2 | 99.090% | 98.530% | 98.843% | +0.896% | +2.323% |
| jump-p2 | 98.003% | 96.822% | 98.216% | +2.175% | +2.870% |
| many-walls | 98.841% | 98.110% | 94.707% | +4.461% | +0.409% |

原契約2はcaseごと3round、original warmup1+3×4child/round=36warm、off/coarse/full warmup1+10×1child/round=30warm。原binの固定3sampleを保持するためchild数が異なる。順序original×4→off→coarse→full、次roundは逆順、全126child exit0を確認。seed1979/192sims/512nodes/depth24/step4、固定6case。gateは事前contract2-method-fixed.jsonの≤5%。対照はoriginalでありoffへ後付け変更しない。fullは全case5%超で参考詳細、原coarse全6caseは通過。負のoverheadは揺れであり高速化ではない。

統括は2roundでoriginal6warm/coarse20warm、交互逆順。全6caseのR_expの最小sampleは97.578%以上、決定的出力と保存則は一致。壁中盤のみ5.131%超過をそのまま残す。2窓をpoolして通過させず、違うwarm数/順序/窓の差と揺れを保持する。今回native速度run0なので、超過頻度・CI・精密なoverhead分布は確定しない。

原runの条件付きH1（>50%）支持は追認できるが、再実行全条件の低歪み成立は追加検証が必要。次は同じ固定gate/制約/全6caseを保ち、事前に窓・反復・warm条件・対照順序とgate判定を固定して無競合測定する。壁caseを選別削除しない。98%は分類比であって固定queueの速度改善予測ではなく、最適化1要因の前後測定が必要。allocation未測定、full詳細時計は参考、Wasm全探索wall未測定、広いUI timeout原因未特定を維持する。

## 問い2: fixture再生成・規約/変換

固定原文は[game.js](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/game.js)、commit751186344fc52ad0c29bc65922e62c6fa915f006、実SHA256 dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5。generator de9b60f531113cc5c92911a6988a8c255de467c3e7be6dcbfb6d68de88aaef44、inputs1c3a0040d7eab9aba4050bc476a4315bce8062142a28db79cb2899cfe404f038。

generate.mjsはimport.meta.url親へfixtures.json、reexecute.pyは__file__親へfixtures/log/executionを書き出す。両コードを先に読み、game.js/inputs/schemaと共に自己fixture-copyへ同bytesコピーし実行。原source/path変更なし、最小path patchも不要。既存VM suffixをそのまま保持し、追加adapter0。2独立Nodeとも1,325,825 bytes、SHA256 **206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb**。原artifact-manifest全30payload/size/hashとsource-manifest11原文hashを照合した。

verify.pyはschema記載のrequired/type/enum/const/array長/rangeを標準Pythonで再帰照合（外部validator未導入）。schema自身はhistory妥当性、feature値、terminal優先を保証しないため、追加でlegal-prefix長=ply（合法20のみ）、key/parity/count、wall anchor→segments、policy mask、136perm自己逆、射影injectivity、pawn jump/斜め着地点と壁offsetを検算。独立壁グラフBFSとFloat32丸めで648feature全値を一致確認。P2は駒/channel入替・cell y→8-y、H segments y→7-y/最終行0、V y→8-y。H8+a→81+a、V72+a→145+a、pawnは方向→実着地cellであり直線jumpを通常1歩へ誤変換しない。

合法20、synthetic-history3、synthetic-total-ply5。getLegalActionsのpawn反復filterは遷移先count<2を要求するがisActionLegalは幾何検査で、3回目return probeは集合false/幾何true。後続adapterは内部各子のhistory集合で判定し、isActionLegalだけを規約Aの合法判定に使わない。実historyではrootを1回数え、overlay push/popと兄弟復帰を検証する。参照generatorのチェックはsource側のみ。

terminal raw maskをeffectiveと区別する。合法goal-winはraw108手が残り、synthetic-goal-at200はraw105手・winner2・rawDraw=trueだがeffective P2win/手番value−1。winner→draw→ongoingの順で判定し、終端effective maskは空/展開0、raw diagnostic maskはそのまま別項目とする。全探索で同じ優先を使う。ply199 count0は人工overrideで実history妥当性を満たさない。runtime通常入力にはcurrent_count≥1、整合history/ply等の検証を要求し、synthetic専用入口だけでこの欠落を明記して扱う。

完全合法200ply replay、実historyで合法手なしdrawへ至る例、Rust overlay/internal expansion/NN/features/numerical parityは未実行。人工fixtureの存在をこれらの完成とみなさない。20legalは生成器で終局前membershipを逐手assertし再生成できたが、synthetic8は到達可能な実局面と主張しない。schemaは最低条件のみで、後続Rust側のinput検証とraw/effective契約を追加する必要がある。

root MIT/source notice/text lineageは保存済みの資料であり、モデルbinary SHA256/graph/PT↔ONNX数値/重みと学習data完全provenance/配布条件の完全性は未確認。今回モデルを取得せず、配布可を認定しない。

## 失敗・未成立・negative result / 再現

本検証は自己copy再生成と独立算術で成功。旧generator SyntaxError/補助比較失敗、旧parent-only方法、full gate超過、UI suite timeoutは元証拠を保持し、消去していない。今回Rust mismatch/最適化negative resultを観測したものではない。short壁caseのgate不成立はそのrunの計測妥当性保留。

成果物と全数値は[summary.json](../../.artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/summary.json)、[verify.py](../../.artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/verify.py)、verify.log、fixture-copy/{fixtures.json,execution.json,rerun-0.log,rerun-1.log}。verify.py SHA25686be5e2ba89b1dd249efa60f69ca7dfbcc00d678ad701f556378b46dc10f73b0、summary SHA25686b044e124fe6c5bb86135abd875509e505b1f399674abb9f0667e0092bf33ed。原analyze-contract2.pyと原reexecute/generateは実行しない。

```bash
timeout 35s taskset -c 0 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B .artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/fixture-copy/reexecute.py
timeout 25s taskset -c 0 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B .artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/verify.py
```

## 書き込み停止 / 資源・保持 / 次判断

開始readyと目標/.8/.4 showでpauseなし、自.8のみclaim。自.4は[時間訂正](ai-sigma-critic-time-correction.md)をnotesへ参照し限定理由で本人close済み。旧報告の30分内という記述は不成立（30分26.649秒）。目標・他担当・実装issueの担当/closeは変更0。

Node PID645981/645989、exit0/0、CPU0、child CPU合計0.142363秒、peak RSS75,336KiB。独立verify最終PID648371、exit0、RSS21,940KiB。19:09:05UTCの/proc確認はこの3PID不在。全自jobは同期回収済み、残background0、他者kill0。Node heap128MiB/各15秒、Python25秒timeout。累積shell/read/BeadsのCPU/RSS瞬間値は完全計上しておらず、0使用やhard cgroup保証とは言わない。1CPU affinity0/RAM1GiB内の短い観測であり、CPU0であることをexperiment性能窓の無競合根拠にしない。

自己artifact論理量1,517,074 bytes、allocated1,552,384 bytes（19:09時点）に最終報告/訂正/logを加えても2MiB未満、64MiB枠内。新規依存/model/build/native速度/正式測定/対戦/学習/GPU/subagent0。自己copy/期待bytes/独立算術/前後hash/旧失敗を保持、削除0。後続のRust内部parity、固定gate無競合再測定、モデルgraph/provenanceを統括判断へ提出する。比較protocolは方式のみでT/m/pool/adapter正式凍結ではない。

最初の最終保存UTC2026-09-30T19:16:24.501796+00:00、経過1247.501796秒で20分上限を47.501796秒超過。期限遵守・最後3分確保は不成立。原因は最終文書生成が19:09から長引き、残り時間の確認/打切りを実施できなかったこと。前回と同様の終了処理管理失敗を再発した。検証内容の成功を契約全面成功とみなさない。追加検証は停止し、限定証拠と予算違反を報告する。訂正保存・書込み停止UTC2026-09-30T19:17:36.423807+00:00、経過1319.423807秒、上限超過119.423807秒。送信前show/backup/reportのみを行う。自.8は受入れ待ちin_progress、目標は閉じない。
