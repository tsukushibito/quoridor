# SIGMA-SEARCH-POLICY-DIFFERENTIAL / quoridor-4lc.94 / 契約1

hypothesis `01a0f31c-2e4b-7170-82c5-69e1428c2418` → coordinator。**次の第一候補は候補Cだけ1.5→1.0の等completed-backup対照。係数採用ではない。** H2に実source差と有限NN0反証を得た。FPU/tie/finishも差を作るが、FPUの実parentQが旧根に欠測し、Cは既存一行差のkernelを利用できるため先に分離しやすい。snapshot変更件数を棋力効果の大きさへ換算しない。H1 wrapper費用/H3残NN・時計/H4標本を保持する。

親現行枠版5/common/実行規約全文・goalを読取、ready/show・pauseなし/本人割当後94のみclaim。受領観測02:05:26.388032UTC、処理02:35:26/newjob02:30:26/提出02:45:26。親05:49:12終了・CPU4/RAM8/global3/保存12GiB内、旧条件変更0。root91/goal/他者操作0、93 live source読取/編集/待機要求0。

コードはGit `65b4252b23045127750144d1f5aa093865eff9bf`、最終run `node-policy-r3`/`python-policy-r2`。77停止版Git `28d6feba`の参照関数、固定Sigma `751186344fc52ad0c29bc65922e62c6fa915f006`原worker SHA f2de9444…fe8faを比較。原版と77のMCTSNode/backup/pickFromVisits本文は一致。自己VMはその3部分だけを実行し、worker・NN・runMCTSを起動しない。候補ORT kernelは停止source-finalのhash `7d6873a7…c2cb`と現tools sourceが一致。現Rust coreも読取、採用変更0。

| 規則 | 候補Rust/ORT pending | 固定Sigma-Web NN-MCTS | source位置 |
| --- | --- | --- | --- |
| C | 1.5 | 1.0 | kernel.rs:9/527、worker:239 |
| 未訪問Q | 0 | parent.qValue−.2√(訪問済child.basePrior和) | kernel:535、worker:221–234 |
| 訪問済Q | 親視点edge.value_sum/visits | −子視点child.valueSum/visits | kernel:535/732、worker:230/257 |
| UのN | √(node.visits+1) | √parent.visitCount | kernel:531、worker:223 |
| score同値 | seed1979/Rust209 hash最小 | 合法順のfirst、比較はstrict > | kernel:541/558、worker:234 |
| finish | visits→prior.total_cmp→seed | visits→first（temp0） | kernel:346、worker:300–305 |
| root計数 | 初回展開をsim1へ含む、edge和=sim−1 | 展開backupをsimloop外、rootVisits=loopSim+1/edge和=loopSim | kernel:626/712、worker:272–296 |
| backup | 葉visit/交互edge符号/親visit、Node valueSumなし | 全Node valueSum/visit、毎親で符号反転 | kernel:732–750、worker:257–260 |

kernel位置は `tools/ai-sigma-ort-search/src/kernel.rs`（停止sourceと同bytes）、worker位置は保存 `sources/docs/mcts_worker.js`。詳細の全12項目・条件/hashは[source-comparison.json](../../.artifacts/ai-sigma/resume-20261002/SEARCH-POLICY/source-comparison.json)。Rust209はpawn着地点昇順→H→V、Sigmaは方向順→各anchor H/V交互で、RuleAのlegal_idsは元順を保つ。`sigma_legal_order`は別関数であり候補探索へ黙って適用しない。P2/跳躍のindexを単なる同列位置とみなさない。Rust f32とJS Numberの蓄積差、候補requested512node/depth24と参照uncappedも残る。reference sim上限はcaller入力、93 live設定は未検査。77公開valueは候補初期root NN値、参照root.qValueで、候補の公開値をFPU parentQと呼ばない。

少数実保存根は旧79から6根/462edgeだけ抽出した。native/Wasm各C差の最初例・tie差の最初例、初期の不変例、private late例という目的抽出で、頻度推定には使わない。**原finish6/6を先gate、base/C1/sqrtN/score-first計24のActionと選択score bitsが旧79と一致、別Python binary32とも一致。** 全765の再計算・全raw/tree copy0。

| 旧根 | finish（原実結果） | 仮想base→C1 | 仮想base→score-first |
| --- | ---: | --- | --- |
| Wasm1:23 | 50 | 60→50 | 60→60 |
| native10:69 | 142 | 142→8 | 142→142 |
| Wasm1:57 | 38 | 90→90 | 90→81 |
| native9:8 | 13 | 142→142 | 142→84 |

対照1:17はC/tie不変、5:34はprivate lateで受理分母へ入れない。この仮想次selectはfinishの置換や実際の次手ではない。旧79/81の765=371native+394Wasm、accepted764/private1/無応答欠測1、matched97組/194根、C46/sqrt19/tie114の限定受入れを参照し再集計0。N=sim=edge和+1はfresh/completed source条件からの復元で直接raw nodevisits観測ではない。実6根と旧765のparentQ欠測を保持しFPU補完0。

人工counterexampleは原Sigma classのbestChild/backup/finishを実行した。N10/訪問済basePrior約.8でFPU減算約.178885。parentQ−.4では未訪問Q0のAction5がFPUで3へ、parentQ+.7では訪問済Qを.8とした別rootで3→5へ変わる。parentQ既知の人工例であり、実根・NN・棋力結果ではない。同一rootのC/N/tie等を固定して未訪問Qだけ変えるf32対照を別Pythonでも確認した。

人工exact-score-tieは候補seed→Action5、first→3。equal-visits/prior差のfinishは候補5/参照first3、root展開のみでも同差を確認。depth0/1/2/3×leaf値−1/0/.25/.75の16backupで、親edgeQと−子NodeQが対応した。符号バグを支持する結果ではないが、深木のf32/Number累積・全終端一般性を証明しない。known root初期値.25＋子値−.5ならparentQ=.375、edge-only平均=.5、初期NN=.25であり、どちらもparentQ補完に使えない。

初回 `node-policy-r1` は自己assertが+0/−0を厳密区別し、人工候補の初期+0加算も省略してexit1。source `bd7f3c5`/logを保存し、正しい初期加算と手番視点の数値等価比較へ修正した（`1aa6e67`）。選択score bitsの厳密gateは緩和していない。r2/Python r1は通過、runラベルを結合した最終Gitでr3/Python r2も通過。これは検査器修復でありNN/H2 negativeでも成功棋力標本でもない。

次の案: 同候補backend/model/features/value/order/seed1979/Q0/N式/finish/capsでCだけ変更、固定initial-p1/asym-hv-p2/straight-jump-p2各2条件を**root展開含むK=32 completed backup**で比較する（6検索・名目192backup）。raw numSimsをSigmaのloop数と揃えたと称さない。予測は探索項が減り一部の実snapshotで選択が変わること。root分布/entropy/Action/NNcalls/depth/capを記録し、全3局面で分布が不変ならこの有限対照での感度は弱い。baseline合法/数値不一致なら実験不成立とし効果0へ変換しない。WDL方向や改善を予測しない。

後続samewallは同じ変更を新caller上の結果前固定Tで比較し、配送・原因側の残NN/stop費も記録する。速度・分岐量・深さ/cap/IPCを含む総効果であり、samecompletedとは問いが異なる。親版5の「残処理を相手の時計へ無条件転嫁しない」を守る。93の版/結果/現在作業を変更・待機させず、正式NIや旧WDLへ統合しない。

費用見積りはwriter20分＋確認10分、runtime上限240秒/各job60秒、CPU2 single/NNthread1を次契約で統括が配分する。既存C1 kernelは現C1.5と係数一行だけ違うがbinary/全wrapper bindingは今回未検証、再利用が成立しなければ別許可の研究buildが必要（94 build0）。FPU次案は実parent visit/valueSum/visited basePrior和の少数記録が依存、tie次案はseed→firstとorder因子を分離する。詳細[次一因子計画](../../.artifacts/ai-sigma/resume-20261002/SEARCH-POLICY/next-factor-plan.json)。監督へ追跡可能な効率提案として、既79/81算術を毎回765/全履歴で再gateせず、単一source差＋必要な小counterと修復累積時間を優先する。今回の小診断へ正式freeze/proof層を追加しない。

5監視run合計wall1.020119秒/120秒、4exit0/1checker exit1、guard0。全観測TID CPU0、親+子RSS最大75,943,936B、自己17 PID/starttick現在不在。02:21:54に本文前停止/必要source afterを保存、必要7参照hash不変。短command/Git/Beadsの副次CPU/RSS・瞬間peak/全期間遵守は未保証。既保持5,664,768Bと今回保持を有効16MiB予約内へ加算し、未使用予約と保持実量を別にする。旧peak/成果を減額・削除0、追加予約0、最終量はmanifest参照。

再現: `timeout 60s taskset -c 0 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 tools/ai-sigma-search-policy-differential/supervise.py <new-node-run> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot tools/ai-sigma-search-policy-differential/probe.cjs`、続けて別runで同supervise＋`python3 tools/ai-sigma-search-policy-differential/check-python.py`。専用TMP/XDG、RSS896MiB、合計120秒、期限/combined14MiBを監視する。期限後再実行は別の現在配分に従う。

詳細: [NN0結果](../../.artifacts/ai-sigma/resume-20261002/SEARCH-POLICY/node-result.json)、[別Python](../../.artifacts/ai-sigma/resume-20261002/SEARCH-POLICY/python-result.json)、small-input/input-references/input-after/checker-fix、各*.started/process/log、[自己停止](../../.artifacts/ai-sigma/resume-20261002/SEARCH-POLICY/runtime-source-stopped-before-report.json)。自己コード/実runはGit参照、モデル/全共有source/raw複製0。NN/Chrome/ORT/model-load/全MCTS/対局/holdout/build/取得/委譲0。書込/自己runtime停止、旧79/v1/v2・旧WDL不変、Atract/BORT/CB0、NI/目標未達/過去失敗と未確認を保持。受入れ確認担当coordinator、自94提出後追加研究0。停止→pause/show→backup/report。
