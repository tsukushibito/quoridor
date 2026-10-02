# 中盤の同入力・deep node比較（132・枠9）

原政策固定の4中盤入力でK32の8検索が完了した。根4組と、先着8node枠の中で共有したnonroot9組は、history/Action path/648features bits/137NN/葉手番valueが一致し、親視点へ反転したbackupの符号も一致した。一方、後半2入力の実選択Actionが分かれた。観測範囲で正しさの不一致はなく、A/B複数規則の束による探索配分差の先に手品質を調べる材料が得られた。C/FPU採用・性能改善・119敗因・正式公平性/NI/Sigma同等は認定しない。

| 元保存線 | 新公開手数 / totalply / 手番 | A / B Action ID | root訪問TV | A / B NN |
| --- | --- | --- | --- | --- |
| pair1-color1 | 8 / 12 / P1 | 30 / 30 | .774194 | 32 / 32 |
| pair1-color1 | 16 / 20 / P1 | 21 / 21 | .806452 | 32 / 32 |
| pair2-color2 | 8 / 13 / P2 | 161 / 133 | .645161 | 32 / 32 |
| pair2-color2 | 16 / 21 / P2 | 32 / 42 | .838710 | 32 / 32 |

新手数は元prefixの4/5手を含まない。元119の公開Actionと棋譜が一致した部分だけを用い、browser main RuleAで全history/key/壁残数/合法集合/非終端を復元し、固定入力SHAをAI load前に保存した。入力の補充・変更・有利な差替えは0。事後敗戦線の目的抽出でありIID/代表/holdoutではない。元pair1/pair2 archiveの必要browser-result memberだけを参照し、元成果は変更していない。

全8検索の実rootN32/edge和31を確認。候補sim32、参照はroot展開loop外+31loop、raw参照sim31である。primary256backup/256NN、terminal-noNN0、計測parity32backup/32NNとstartup固定6は別分母。K未到達/timeout/数値・入力・trace不成立/未実施は0。sameK≠sameNN≠sameCPU≠samewallであり、この入力では偶然NN数も同じだった。500ms採用/対局評価は行わず、game/rollout/holdoutは0。

候補private baselineは元source/manifest/lockと既toolchain/flagsでoffline/locked再buildし、immutable Wasm 1f54d0…78a01とbytes一致した。初回private共通targetではtrace buildがbaselineを再利用したためNN前に検出し、variant別targetへ修正した。旧build結果を保持し、正しいtrace binary SHA6f050a754c512b0a160f519ac8924f0c9d887d9860121386536a076d44fa0b3dを配信した。元kernel/共有crate/モデルへの編集は0。private kernel/libの変更patchを保存し、選択/評価/backup計算/finishを変えず、backup前後のread-only recorderとtrace取得ABIを追加した。

最初の固定入力の原/計測K8、両engine計4検索でCP Action/訪問分布/NN/depth/capsが一致した後だけK32へ進んだ。K8 wrapperは候補323.850→444.820ms、参照343.930→278.730msだった。各1回なので計測overheadや速度改善の推定には使わない。原成功K32を再実行・置換していない。

各primary検索のroot+先着最大7unique nonroot計8node、双方合計64nodeを保存した。共有root4/nonroot9、各engineの選定32node中19は未共有の欠測。対応はkeyだけでなくtotalply/history/経路Action/side/featuresを確認した。対応したNN/valueは全てbit一致・最大差0、事前mixed abs1e−4+rtol1e−4も満たした。共有deepのleaf valueとbackup符号、全64選定nodeのshape/finite/strict[-1,1]と自己backup符号を保存算術で確認した。候補親edgeのvalue_sumと参照child.valueSumは反対視点なので符号反転して比較し、候補に存在しないnode.valueSum/parentQを補完していない。

全primary traceは非終端だった。terminal/winner欄を保存したが、実terminal-noNN backupの解釈は今回未観測である。人工NN0符号probeを実terminal検証へ格上げしない。新中盤根の固定golden NN参照はなく、P1/P2両側の自己gateと同入力照合である。未共有state・未選定node・全深部/真ルール独立性・一般tree一致は未確認。最終累積valueSum/visitsが異なることを同じ1評価のbackup不一致と混同しない。

出口は「同評価で実Action差」の枝。現政策を維持し、次案は1つだけ、130P2の条件付き局所手品質対照をこの固定入力3/4へ別配分すること。A/B採用手を1手だけ固定し、その後を同じ固定Sigma continuationへ揃え、全枝を結果前登録する。政策依存の診断であり真の長期正解オラクルではない。今回はそのrolloutを開始せず、参照分布への接近を改善基準としない。単独C/FPU因果は未特定。

## 版・再現・回収

測定source Git edbf29ac29208616a8d20b859db497acb30f0f42、run deep132-measure-r1。保存helper/summary mapping修復 afd8b13。初回summaryのstarted_search_requests=0は汎用started欄が存在しないdefaultの記録器不具合であり、browser-resultの明示started_parity4/started_primary8と全12行が実分母である。rawを変更せず、今後のsummaryを修復した。input抽出draftのrequest ID/list index誤り、private build artifact再利用とともにhelper-failures.jsonへ保持した。検査器不具合をNN不一致/棋力negativeへ変換しない。

再現条件/command/source/binary SHAはresearch-data/ai-sigma/132-deep-node-comparison/{run-config,preregister,build-binding,served-source-after}.jsonとアーカイブ内process/configへ保存。元130handoff SHA f263e130…fd772、モデルd790dac…908d/ORT1.21.0 CPU各1thread、候補C1.5/参照C1FPU.2/order/tie/caps/seed1979は固定。private baseline一致は本人確認であり独立再証明ではない。旧commandの当時期限を自動再実行する許可は含まない。

2専用Worker/モデルsessionを保持し、各count要求を両旧zero後に孤立実行した。通常実gameの相手t0旧ACK非前提を変更していない。browser内で入力/合法性/数値/比較を生成し、Nodeは起動/外資源監視/障害回収/終了後保存のみ、毎手Node timer/referee/CP binding0。API await/wholewrapperは純NN/kernelCPUではない。prepare内部・stop費の細分span、途中clock drift/exactAtomicstore/背景CPU/終了子CPU完全計上は欠測で、start/end Workerclockを別保存した。

本文前停止正本 runtime-source-stopped-before-report.json SHA e6bf3699666645cb4f66c4d0bf234b2e8dd4a2ecc300c333cdefde49d204d9e8。Model2/search handles/activeNN0、main timer-message0、monitor全callback wait、inner forced controlled回収/outer sole-root-subreeper ownedwait/remainingunknown0を分離保存。141 PID/starttick identity現在不在を自然終了/全期間遵守に読み替えない。build20.977456秒、browser25.258924秒、puremock .152618秒、current RSS観測peak1,601,388,544B、guard停止0。build CPU[0]1logical/jobs1、Chrome CPU[2]1logical/ORT各1threadを直列実行した。ru_maxrss/継承highwaterとcurrent RSSは別。瞬間peak/全host無負荷は保証しない。

必要raw/失敗/停止/2binaryをall-attempts.tar.gzへ保存し64member stream復元SHA一致。archive-manifest.jsonが復元先と各memberを示す。モデル/共有依存/full targetは複製しない。現在自己保持量70,590,464Bは保存448MiB guard内、非build runのstorage観測は未使用build targetを除くため全現在量と区別した。保存/復元後に自域未使用targetだけ整理可能で、読み手の必要binary/rawは保持する。統括へ停止版を渡し、独立確認と有限受入れは後続判断に残す。
