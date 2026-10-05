# Sigma固定参照とRust B0の初期仮説調査

Beads issue / 実験ID / 試行 / 契約版 / 報告元スレッド:
目標 quoridor-4lc、子issue quoridor-4lc.2 / SIGMA-HYP-INITIAL / 1 / 子契約1・目標契約1 / hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418。
報告先 coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。契約正本は [目標](../design/ai-sigma-research-goal.md) と [子契約](../design/ai-sigma-contract-hypothesis-initial.md)。本報告の受入対象は調査の再現性。棋力達成や候補の採用を主張しない。

## 判別した問い / 仮説

現B0にはNNがなく、Sigmaとは評価器だけでなく規約・探索経路・資源設定も異なる。現時点で「BFSが最大の原因」「PVを移植すれば同等」「solverが差の主因」のいずれも実測根拠がない。次の投資を決めるには、B0内訳計測と参照条件の固定を先に小さく行い、その結果から速度・評価品質・探索・終盤の枝を選ぶことを提案する。これは固定した実装順の採択ではない。

## 実施内容 / コード・差分・環境・入力の参照

指定worktree /workspaces/quoridor/.worktree/ai-sigma、branch codex/ai-sigma、HEAD 1482df8da6dd91c95db211aeaa914af775b2bc76 を読取確認。初期移入差分は /workspaces/quoridor/.artifacts/research-team/sigma-launch/launch.json。17:28 UTC頃の tracked diff は `git diff --binary HEAD` 34,765 bytes、SHA256 e1deeeb5805b598a7833b2233bf623faee357cacc67c485f8b263dd31797a949。未追跡の契約・チーム文書は後掲の実hashで補完する。HEADだけを入力識別に使わない。

AGENTS、目標/子契約全文、common/role、チーム設計、AI設計§8・14.4・14.5、storage policy、Beads workflow、handoffを確認。ready、目標/子issue show後に自分の子issueのみclaim。既存ソース、bridge、native診断CLI、Phase 3報告を限定読取。別worktree・M2・UI作業は開始していない。

Sigmaは [GitHub repository](https://github.com/bartolomeo3000/SigmaQuoridor) とAPIを実際に参照し、main取得時のcommit **751186344fc52ad0c29bc65922e62c6fa915f006**（committer date 2026-08-22T21:14:55Z）を固定してrawテキストを取得・hash化した。以降の根拠はすべてこのcommitであり、現在配信されるGitHub Pagesとの一致は未確認。全体clone・モデルdownload・環境導入は行わず、15個の小さいテキスト応答をメモリで読んだ。別manifest・依存lockfileらしい名前はこのcommitのtree探索では見つからなかった。全内容を監査したという意味ではない。

## 観測結果と数値 / 根拠

以下はコードとメタデータの読取観測であり、実行性能・対戦成績の実測ではない。

### 固定Sigma参照候補と確定できない点

| 項目 | 固定commitで確認した内容 | 比較に残る判断・未確認 |
| --- | --- | --- |
| Webモデル | 9×9/各10壁、既定 docs/models_9x9/best.onnx。app.jsはPCR 250と表示、export_onnx.pyは runs/models_9x9_pcr/best.pt を出所とする | 実ファイルの重み・演算・SHA256は未取得。READMEのscratch 321の説明を既定モデルと同一視しない |
| モデルmetadata | ONNX 11,663,428 bytes、Git blob SHA1 f23802a83dc9054b5227da74b3771698854535f0。出所PT 11,718,115 bytes、blob eed997da36e5bf758cbc46080fcca13b47bb4f87 | Git blob SHA1はファイルSHA256ではない。export再実行によるPT/ONNX一致、実モデルschema manifest、配信bytes一致は未確認 |
| Web推論 | ORT Web WASM provider、CDN WASMパス1.21.0。float32入力 [1,8,9,9]、policy_logitsとvalueを読む | numThreadsはisolation有ならhardwareConcurrencyを最大8に制限、有効条件次第で1。単一CPU比較には明示的な1設定と実行検証が必要。ローカルort.min.jsの版一致は未確認 |
| 特徴 | 手番側に正規化した自駒/相手駒、H/V壁の「辺segment」、自/相手残壁のscalar plane、両側のゴールBFS距離map。P2は縦反転、残壁/10、距離/80 | Rustは壁anchorのu64。壁anchorをそのまま入力planeにしてはいけない。モデル実bytesから演算精度/graphを確認する必要あり |
| Action/value | Sigmaは9×9で136 logits = 8駒方向+64H+64V。直線jumpは方向のまま着地点を変える。P2 policyは縦反転permutation。valueは手番側 [-1,1]、head tanh | Rustは209 IDs = 81着地点+64H+64V。合法手について方向↔着地点と壁offsetを変換する必要あり。モデルpathによるfull-canonical判別を新manifestへ明示すべき |
| 壁規約 | overlap/crossing禁止、両側到達必須。C++は壁anchor/segment bitset、固定配列BFS、既知経路と壁接触数でBFSを省ける候補を判定 | Rustと合法壁集合が等しいことは未実行。論理上の省略条件をコピーしただけでは正しさの根拠にならない |
| 反復・終局 | JS/C++とも3回目の同一局面を生む駒手を合法集合から除く。Webは200 pliesまたは合法手なしでdraw | Rust標準規約は反復手禁止も自動手数drawも持たない。同一規約の評価adapterを勝敗前に決める必要あり |
| 探索予算 | Web既定はdesktop100/mobile50 simulations、temperature0、C_PUCT1.0/FPU0.2。root expansionはloop外 | B0はroot expansionも1 simulationとして数える。固定sim数の比較ではeval数/root visitsも併記。現在両方とも本格的な実時間deadline APIは未確認 |
| 木/TT/solver | WebはrunMCTSごと新root、調べたNN-MCTS経路にexact solver/NN-cacheなし。Python MCTSは2 ply内subtree reuse。C++ selfplayはNN TTとalpha-beta/leaf solverを持つ | 「Sigma」という名称だけではnative/Web/selfplayの機能が一致しない。Webのminimax agentをNN-MCTSのexact solverと混同しない |
| native評価経路 | tournament.hppは着手後arenaをclear、共有NN TTなし、AgentSpec C_PUCT1.0/FPU0.1。調べた同fileにはsolver接続なし。tournament_cpp.pyはtorch推論でCUDA/MPS/CPUを自動選択し、既定8探索threads | --threads 1だけではtorch/GPU/推論thread/並行対局を制限できない。native参照adapterを選び、CPU推論全体とleaf_batchを固定する必要あり |
| ライセンス | root LICENSEはMIT、READMEはそこへ参照。固定treeに別model-license/manifestらしい名前は見つからない | モデル固有の追加条件・第三者由来・配布provenanceは未確定。MIT表示は確認事実、採用可否の法的判断は本調査でしない |

各行の根拠: [app.js L5–15/L122–134/L1263–1274](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/app.js#L1263)、[export_onnx.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/export_onnx.py)、[Web worker L21–101/L198–294](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/mcts_worker.js#L21)、[JS game L9–49/L296–408/L578–643](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/game.js#L578)、[C++ engine L161–209/L362–411/L458–490](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/engine.hpp#L362)、[rules L149–167](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/RULES.md#L149)、[network contract L148/L327 onward](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/dual_network.py#L148)、[Python reuse L540–609](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/mcts.py#L540)、[C++ tournament L14–17/L47–53/L606–612](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/tournament.hpp#L14)、[native driver](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/tournament_cpp.py#L54)、[MIT](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/LICENSE)。モデルmetadataは固定commit recursive tree APIの該当pathのsize/shaから得た。manifestを取得したという主張ではない。

### Rust B0の実コード

[quoridor-core position](../../crates/quoridor-core/src/position.rs) のlegal_action_idsは128壁候補を走査し、衝突条件を通った候補ごとに両側到達を調べる。wall_distanceはVecDequeを確保して壁のみのBFS。playは合法性を再検査する。壁のu64表現は既存なので全面置換を既定にしない（L63–69/L155–179/L215–294）。

[quoridor-ai](../../crates/quoridor-ai/src/lib.rs) はB0Evaluatorの距離差・残壁差のtanh value、駒移動距離と固定壁weight prior、相手即勝ち脅威の例外を使う（L49–98）。PUCT1.5、未訪問Q0、全edge走査、simulationごとpath Vec、展開ごとlegal/policy/edges確保。深さ/ノード上限時はヒューリスティックへ戻り、proofにはしない。最大4096 sims/2048 nodes/depth48/arena64MiB。newごと新root、NN/cache/reuse/solverなし（L159–190/L239–380）。

[core game](../../crates/quoridor-core/src/game.rs) のhistoryは保存/undo用で反復手を除かない。AIへ渡す[Snapshot](../../crates/quoridor-wasm/src/wire.rs)は盤面・turn・ply等で、反復countsは入っていない。[Wasm AiSearch](../../crates/quoridor-wasm/src/lib.rs)はB0生成・step・finishを公開し、[Worker](../../packages/engine-bridge/src/ai.worker.ts)はsetTimeoutで分割、1–16 sims程度をslice時間で調整する。これは1手の同実時間予算をまだ実装していない。[client](../../packages/engine-bridge/src/ai-client.ts)の45秒は障害watchdogであり公平な思考時間設定ではない。

既存 [Phase 3報告](phase3-baseline-ai.md) は192-sim native約20–22ms等を別日の測定として記録している。本機材/今回入力での再測定ではない。報告自身も棋力未benchmarkと明記。今回これを改善証拠やブラウザ総時間へ換算しない。既存失敗記録のundo修正はUI境界の不具合で、探索高速化/PV/solverのnegative resultではない。限定調査でSigma改善の過去negative resultは見つからず、網羅的不存在は未確認。

### solverに関する独立検証候補

[alpha-beta L160–187](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/alphabeta.hpp#L160) はzhashでTTを参照した後に、history/pathで合法集合を作る。history依存規約で同盤面の再利用が妥当かはコードコメントだけで確定できない。同history baseで経路履歴を変えたcaseのTT有無比較をcriticへ提案する。これは潜在懸念であって再現したバグではない。timeout時はreturned valueが未証明になる契約を守る必要がある。さらに[leaf solver呼出し L770–787](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/selfplay.hpp#L770) がsimulation overlayをsolverへどう引き渡すかも要確認。Web経路の比較にsolverがないため、これをWeb棋力差の説明と決めつけない。

## 競合仮説 / 予測 / 反証となる観測 / 最小判別実験

以下の費用・閾値はすべて次契約の**提案**。今回実行していない。各実験は元B0を対照にし、内容の異なる変更を一度に入れない。統括/criticが予算・固定条件を決める。

1. **H1: B0では合法壁の到達判定と重複BFS/確保が速度の主要因。** 根拠は上記Rustの各壁候補BFSとplay再検査、対してSigma C++の固定queue/既知経路省略。予測は展開コストの半分以上が合法手/BFSで、固定探索量の改善余地が大きい。否定はその割合20%未満、または局面全体の速度差を説明しないこと。最小実験は既存CLIの3局面（192 sims、seed1979、512 nodes/depth24）で合法手・距離・evaluate・transition・selectの排他的時間、BFS回数・確保回数を計測。inclusive時間を足し合わせない。必要なら固定配列queueだけの試作を1個比較し、合法集合/距離/transition/seed結果を照合。見積り30–45分実装、実行5分以内/1 CPU、モデルなし。計測挿入の歪み、初期3局面への偏り、手の列挙順変化がリスク。主時間割合が小さいならBFS最適化の優先度を下げる。
2. **H2: 速度よりB0のpolicy/value情報不足が棋力差を生む。** 根拠は均一な壁priorと距離評価対Sigma PV。予測はルール/探索を同じにしても固定小探索量でPVが戦術・壁選択を改善する。否定は正しい変換が確認されたPVでもholdout局面の手の品質/paired対戦が改善しないこと。最小実験は固定モデルを後続契約で取得・hashし、20–40個の両手番/壁/jump局面で特徴・合法logits・valueの参照一致を先に検証し、同PUCTのB0/PVを1/32/128程度の分析予算で比較する。参照一致前の低成績は実装失敗であり仮説のnegative resultではない。推定1–2時間/CPU1/GPU0、ONNX約11.7MB＋専用backend環境は基盤配分待ち。持ち時間同等の評価は別に必要。相手に合わせた局面選択・value sign・P2 permutation・反復規約・未検証モデル条件が交絡。
3. **H3: PVを入れた後はCPU NN推論/特徴生成が支配し、H1のコア高速化だけでは同時間の探索量が伸びない。** 現B0にNNはないので、これは将来B1の実行方式の仮説。根拠は8-plane conv netとWebの1-leaf ORT、複数thread既定、およびRust CPU backend未導入。予測は単一thread batch1で推論＋featureの比率70%以上。否定は比率20%未満か、明確にルール側が支配すること。最小実験は同じモデル/固定入力10個のwarm/cold推論とfeature-onlyをnative/Web別々に計測し、数値parity・p50/p95・memoryを記録。ONNX実graphを調べ、Rust候補backendが動くかのcompile/演算対応は別検証とする。推定30–60分（環境が用意済みなら）/CPU1、モデル取得はH2と共有、GPU0。ORT↔Rust・SIMD・Web yield・deserialization・cold start・暗黙threadが交絡。固定速度から棋力へ直接推論しない。
4. **H4: 探索の訪問配分/上限到達が評価器差と同程度に重要。** 根拠はB0のQ0/FPUなし/2048-node・depth48上限とSigmaのdynamic FPU。ただし固定Webも木を毎手捨てるので、reuse欠如はWebとの確定差ではない。予測はFPU変更またはnode/depth上限の単独変更で同量評価のroot分布・cap-hit率・局面解決率が改善する。否定はcap-hitがほぼなく、同評価器のpaired比較で効果がないこと。最小実験はB0 unchanged、FPUだけ変更、上限だけ変更の3枝を固定eval数/seed/局面で比較し、枝ごとのRAMと同時間対戦を別記。見積り30–60分/CPU1、モデル不要でも始められる。FPU係数をSigmaからそのまま移す根拠はない。学習なしでも試せるが、tie-break/cpuct/評価スケールとの相互作用に注意。tree reuse/NN cacheはhit率ログが取れる後続枝に残す。
5. **H5: 終盤のheuristic誤判定が実戦損失を集中させ、無壁solverが安い棋力改善になる。** 根拠はB0の壁のみ距離と有限depth、対して固定壁下でも駒衝突・jump・手番・cycleが残ること。Sigma selfplayのexact solverは参考だが、Web NN-MCTSでの搭載は確認できない。予測は合法な双方無壁holdoutでB0の手が独立W/L/D oracleと食い違い、solver有で減る。否定は不一致が少ない/該当局面が少ない/構築時間が持ち時間を超え効果が消えること。最小実験はまず合法20壁配置を経た少数fixtureに固定し、81×80×2以下の局面グラフを分析上の無反復禁止規約で解き、既存B0の選択と比較。元の規約とSigma反復禁止規約を混ぜない。見積り1–2時間試作/CPU1、コード予算と正しさの独立検証を次契約で配分。timer切れはUnknown。残壁ありの全探索や大規模DB生成は提案していない。history込み規約をこの状態数だけで解けると主張しない。

維持対照: 既存B0の評価・合法手・PUCT・seed/orderを保持し、現CLIとbrowser観測を再現する枝を残す。H1で壁処理が支配しない、H2の互換性が難しい、H5の終盤出現が少ない場合に、大きい変更を一括導入する理由はない。いずれの仮説にも現時点の棋力差の実測がないことは共通する。

## 次の提案 / 必要な判断

最も安い次の判断材料は、experimentによるH1の排他的内訳計測と、criticによる反復/手数/資源/参照経路の固定。これは本報告から別契約を統括が作る提案であり、当役は追加依頼/実験を起動していない。後続のモデル取得を選ぶなら、固定treeのONNX path/size/blobを照合してSHA256・実graph・出所条件を保存し、まずP2とjump変換のparityを通す。

native基準案は同commitのどの経路を使うかを名称で明示する。C++ tournament+CPU torch、Python MCTS+CPU torch、固定Web JS+ORTは異なる条件。C++にsolver/TTを追加するなら「固定upstream tournamentをそのまま実行した」と表現しない。製品ブラウザ比較は固定Web worker+同ONNX、ORT numThreads1、GPUなし、分析worker/先読み無効、同機材。単一thread化など参照変更は小さい差分/hashと目的を記録する。browser UIのsim slider値を同時間条件と呼ばない。

持ち時間案: warmupした単一thread latencyを両者で測った後、同じwall-clock予算候補0.1/0.5/1.0秒などから予算内で安定する1条件を勝敗前に決める。候補数字は採択済みでない。root expansion、feature/inference、adapter処理、deadline超過の計測範囲、最終有効手とtimeout扱いを統一する。既存B0はsimulation limitしか持たないためdeadline adapterの追加が必要。異種のsim数一致は分析用だけに使う。

規約案: 比較専用adapterが双方へSigmaの3回目反復手禁止・200-ply規約を供給する条件を検討できる。ただしhistory合法集合がRust search/snapshotへ伝わる実装が必要で、製品標準ルールを黙って変えない。代案は双方を標準規約へ揃えたSigma変更版を別基準として固定すること。共通審判がrootの不正手を拒否するだけでは内部探索規約の一致にならない。

非劣性案: 合法な複数開始手順をholdoutに固定し、先後ペアごとに評価。temperature、seed、draw/timeout、無効対局扱いを事前決定。score=(W+0.5D)/N、許容差5 pointsなら片側95%下限>0.45等を候補にする。ペアを不確実性評価単位とし、200 gamesは探索的開始数で精度保証でない。対戦結果を見て基準/停止数を変えない。統括+criticが固定し、native/browserで別の到達判定を行う。

## 支持する結論 / 支持しない結論 / 交絡要因と未確認

支持: 固定commitと重要text hash、上記のコード上の機能差、モデルpath/size/blob、規約/資源差は再読取可能。
支持しない: どの仮説が主因か、B0とSigmaの実戦差、同PC/単一CPUの速度、モデル移植互換性、solver正しさ、ブラウザでの棋力達成。
未確認: 配信版の一致、ONNX SHA256・実graph・モデル固有provenance、ORT/torch実threads、実時間adapter、ライセンス適用のモデル個別確認、固定局面集合/評価の統計条件、プロセス競合時の性能。GPU多数対局selfplayの作者速度やREADMEの内部Eloを本機材単一CPUの根拠にしない。

## 実装失敗・実験不成立・negative resultの区別

今回は読取調査のみ。対戦・速度測定・NN実行・実装・学習を実施しておらず、性能negative resultも実装失敗もない。読取コマンドは正常終了し、clone/model download/長時間ジョブは0件。報告書の初回whitespace検査は末尾空行でexit3となり、末尾空行を除去して再検査した。これは文書整形の修正で、研究実装の失敗ではない。未確認は未確認として残す。独立再実行・critic受入れは未実施であり、report配送受領と研究受入れを区別する。

## 再現コマンド / 独立再実行の状況

実行済み読取の中心は、各10–25秒timeout付きの `rg --files`、`rg -n`、`cat`、`sed -n`、`git rev-parse HEAD`、`git branch --show-current`、`git status --short`、`git diff --binary HEAD`、`lscpu`、Python標準urllib/json/hashlib。raw fetchは下記形式を各pathへ適用し、モデルpathをfetchしていない。URL/hash/pathは後掲manifest。手順に乱数はなく、研究seed/入力モデルは未使用。

```bash
timeout 18s python3 - <<'PY'
import urllib.request, hashlib
commit = '751186344fc52ad0c29bc65922e62c6fa915f006'
path = 'docs/mcts_worker.js'  # 後掲text pathのみを指定
url = 'https://raw.githubusercontent.com/bartolomeo3000/SigmaQuoridor/' + commit + '/' + path
data = urllib.request.urlopen(url, timeout=12).read(200000)
print(path, len(data), hashlib.sha256(data).hexdigest())
PY
```

commit/モデルmetadata再読取: GitHub API `/repos/bartolomeo3000/SigmaQuoridor/commits/main` は将来変わるため、再検証は固定commitの `/git/trees/751186344fc52ad0c29bc65922e62c6fa915f006?recursive=1` を使う。committer dateは初回API観測。モデルblobのAPI endpointはmetadata識別のためで、今回は内容を取得しない。

既存CLIの後続実験候補（今回は実行していない）: `cargo run --quiet --release --locked -p quoridor-ai --bin measure_native`。これは3局面・192 sims/seed1979/512 nodes/depth24・warmup1+sample3のnative診断であり、対戦ハーネスでもbrowser latencyでもない。compile資源・CPU競合・追加内訳instrumentationは別契約で管理する。

読取環境: Linux 6.18.40.1-microsoft-standard-WSL2 x86_64 / glibc2.36、lscpu表示 Intel Core i5-14600KF / 20 logical CPUs。正式測定をしていないため実効thread制限、clock governor、P/E core割当、計測ブラウザ、温度は未固定。機材のCPUが20でも今回の配分は1 CPUで、重いjobは起動していない。lockfilesは後掲hash、環境/toolchainは更新していない。

### 読取入力manifest（SHA256）

| Local path | SHA256 |
| --- | --- |
| AGENTS.md | c03050bdfe00ecf86558945f0100ca6265d33e7447743cc277aeffea546f6edb |
| docs/design/ai-sigma-research-goal.md | 4b0fee4e7b7c9f2de07a6baf0c2fd5f649718511e419366af9464471d4524b7d |
| docs/design/ai-sigma-contract-hypothesis-initial.md | ad42b770c7ac478e1995f35a78cfeb2abcf4dc3fda1eefd1861cb70b67dbde1a |
| docs/design/ai-research-team.md | 13d757d4cad2b68d1ad1fb106360b91108cbcce0d74718ac1813599635eab123 |
| docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md | c4dbe22719bcd60ad0c9e8586a37d4e0be6bcc2dbd863cea21f8e322093ab577 |
| .agents/research-team/common.md | 56c4d2aed25c083e6292d11efb0afa2c70a8f26709e5ad5a50029c8ef8d55add |
| .agents/research-team/roles/hypothesis.md | abfc3049d891db3da8fdab19a34c41bc1ed38aeda31b049015ba6f02390ef66c |
| .agents/research-team/templates/handoff.md | 8139c0ad5a3a4eccc5ba7654807effa350debfcc32c5320aeffba4e9b8e2f753 |
| .devcontainer/storage-policy.md | bc27c254d4cde6342329d9f27c376da786857d58ea8b6cf0ea5e0ba78fabb099 |
| docs/development/beads-workflow.md | 3d37cee35946f0362e03ac96f6d3265e319adf082fee9eab4089da86be95645f |
| crates/quoridor-core/src/position.rs | 0a2a1c26e6d4e5fb41fb58b69c92ab5f1d082b8e2da2dc26440b2eaec22d57f7 |
| crates/quoridor-core/src/game.rs | 543995676fb46cc4e80d0fccb650875eb901a4b4d71187788ee09dfbaf01a420 |
| crates/quoridor-ai/src/lib.rs | f18b5a2b9bcdf0646a1eccaca9e5191884a6910a66fe3e22fe03ec7a329ebdec |
| crates/quoridor-ai/src/bin/measure_native.rs | a32ec56a90cfb25469100cc7b3ecfb9c5976bd81d52dd51855280668cd791d2b |
| crates/quoridor-wasm/src/lib.rs | 7e5f55ac25b3ffdee5e7f5ddca4de2f9a022d58aeac67d68ccc3be3b8344ce94 |
| crates/quoridor-wasm/src/wire.rs | 4a28ac6169e32e3ff34681d7b1ea8617a485f9557260a885980c1ec2fd5364a2 |
| packages/engine-bridge/src/ai.worker.ts | d88394b5bacc5ead5d205e4616a186ae7ec67135c44f7293367d46258c535aa6 |
| packages/engine-bridge/src/ai-client.ts | e7d24902bec241fc10afdffb2d67e1184913f7b872a618863dba5581c9fd6b6b |
| packages/engine-bridge/src/protocol.ts | 583a1fa005309ef0a85d368fd50a287157b2de20178cf3fe7f7d0f865db369ce |
| docs/reports/phase3-baseline-ai.md | 487a56cf12f57a0000e074ba672a0275de2e2856f871f828a25adab0737b2b45 |
| Cargo.lock | f1b7e28714344098c70588371a8869a128612c40e0762c4cd0fbc0677309f346 |
| package-lock.json | 00623ab83b120debff85f750fad8b056f0bc55bd9f85385025d401629776e56e |
| tools/training/uv.lock | 6b562f85005518a8e38556722d536c342c17da18b0d7040fcd0e80bb662671b3 |
| tools/research-team/uv.lock | d0c4f15d3beebfd2f5c37d76cebd8dcbcd562e79b3c357721dba2d8961e00658 |
| rust-toolchain.toml | a295155a0b138ee09d908306393d2778135ebaab96cfbc29ea0a6cd647563b53 |
| /workspaces/quoridor/.artifacts/research-team/sigma-launch/launch.json | 306b71b7d1a0363a363450e5cba2f4315970eb82378fa85597b2388dca926d28 |

| 固定Sigma text path | bytes | SHA256 |
| --- | ---: | --- |
| README.md | 32959 | 4446f2bd6a6c3c7584f3ae1688b52797c56a96d1c4d03e715cf159c66b7c34ae |
| LICENSE | 1071 | b5e277822da3c9eb54eb04e9ee3c4f93bfeb769c829d5d0f70c99835a2f6733d |
| RULES.md | 8955 | 52a2669b824ca95a78a76c3bbc0016a4ac08e16b90099b2af49491341e1728ce |
| cpp/engine.hpp | 23271 | 72a674b1b02a680ef375be81d78b33914d125183789a1680c6e4d8dde72c6557 |
| cpp/alphabeta.hpp | 10905 | 454d323261dbda277a880b9b651252890936837b5572fb147d48ee07628ff43d |
| cpp/selfplay.hpp | 51703 | f99487078a29baecda6df75c4d34a3ee2e255829c2467ccbacb7d3d26d55afa8 |
| cpp/tournament.hpp | 22727 | f507cec6ce0e6e77314b89e5b6bd915c293f69506e0cc789131d3fcbd5becad5 |
| mcts.py | 26052 | f17c79e93f360086427cf2799728a3069a97b59d7f3a6855e6f3de80fd728d7c |
| docs/game.js | 27877 | dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5 |
| docs/mcts_worker.js | 17775 | f2de9444e8960ca14d4d4acb5dd319e3f0a6a743c39b4032dce32068ebcfe8fa |
| docs/app.js | 93099 | b585302b0af1295dbea23fe0a59781c568ead0be79fc6bc13ccb2273fe6dc9bd |
| dual_network.py | 27874 | c1b4e74d0cdff688580dd29a3cdea4b5fb498c6020324924936066702f301502 |
| export_onnx.py | 4087 | ab56635c59d00d0cd818ffbdf583c5e881105b204d6cdc7d97bd0718f46be2d8 |
| requirements.txt | 992 | 57e499929e079e280a4ee2535c730cef8a0b6b1e95eb574598fe6ec569a36380 |
| tournament_cpp.py | 32644 | ceb08e9dbc90851838341c5a6a07d56f9d6bd07513879d4a27430a8755f2aa2b |

これらはraw bytesの実SHA256。依存はRust Cargo.lock、npm package-lock、training/research uv.lockをread/hash。Sigma requirements.txtは未version固定の名前列挙で、再現環境lockとしては不十分。モデルbytesは0取得、モデルSHA256は未確認。

## 書き込み停止 / 実行中プロセス・資源の残存

この報告書だけを作成し、保存完了後に書き込みを止める。直接起動した全短時間readコマンドはexit0、バックグラウンド化なし、長時間job/性能計測/学習/GPU/サブエージェント0件。exec session残存なし。共有ホスト/App Serverや他者プロセスを終了していない。送信前は目標と子issueを再showし、pauseがない場合だけbackup sync後にreportする。配送後はBeadsの根拠に保存し、統括受入れ前にcloseしない。

予算実績: text取得合計381991 bytes（メモリ、研究worktreeへの原文保存0）。新規永続成果物は本報告のみ（32 KiB未満を提出前に検査、子割当32MiBの残量は少なくとも33,521,664 bytes）。正式な計算実験0秒/GPU0秒/モデル取得0 bytes/依存cache更新0。短いread/DBコマンドの累積CPU秒とpeak RSSは集計しておらず未確認で、0 CPU使用とは表現しない。LLM/tool基盤の自動保存・共有Beads backupは基盤担当の全体台帳で計上し、当役が測った保存量と混ぜない。調査開始は17:20 UTC頃、書込み停止は2026-09-30 17:36 UTC頃（約16分、30分上限内）。全体締切2026-10-01 01:17:58 UTC、書込み停止時点で残り約7時間41分。計算配分は今回1 CPU/1GiB、GPU0を解放し、次の子契約で再配分する提案。

## 保持する証拠 / 整理できる生成物

本報告のmanifest、固定URL/line、launch.json、Beads操作履歴、既存Phase3測定参照を保持する。原文テキストはURLから再読取可能でディスクコピーを作っていない。削除した生成物はない。最終reportのaccepted JSONと本報告自身のSHA256は配送時のtool履歴/Beads notesに記録する。
