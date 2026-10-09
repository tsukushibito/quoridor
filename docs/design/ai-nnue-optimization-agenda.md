# NNUE棋力と学習サイクルの改善候補

2026-10-05のユーザー指示による研究候補集合。[研究方針](ai-nnue-research.md)を補い、担当・着手状態はBeads、観測と次の判断は[研究知見](../research-findings.md)を正本とする。一覧順は実施順でも全実施の義務でもない。

## 優先度を更新する

探索、評価器・学習、教師生成と学習サイクルをまとめて比較し、最大の障害、期待効果、判別できる不確実性、実装・検証・全工程費用から配分する。独立した課題は編集所有と実CPU/RAM/GPU・測定干渉を調整して並行できる。学習分析の完了を探索高速化の恒久的な開始条件にしない。

小試験の不成功から方式全体を棄却しない。実験の不成立、学習量不足、独立データ不足、教師・分布・実装の問題、特定条件での利益不支持を区別する。重要な保留案の再検討契機、同じ問いを続ける理由又は切り替える理由を研究知見へ短く残す。全候補を同時に実装することや、一度に一条件しか許さないことを規約にしない。

Rootは偏り・機会損失・早すぎる断念を観測と全工程費から検討し、重要な方向変更を人間へ提示する。独立レビューは前提・主張・採用判断に必要な時だけ依頼し、固定監督役や定期LLM点検を設けない。

## 探索の正確性を保つ高速化

| 候補             | 調べること                                                                                                            |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| 手をまたぐ置換表 | プレイヤー別の再利用、モデル/規則/探索条件の識別、世代・深さ・boundによる更新と容量。反復履歴による評価差を混同しない |
| 局面key・履歴    | 増分hash、反復回数、make/unmake、コンパクトなTTと履歴keyの費用                                                        |
| 合法手・経路     | 壁の重なり/到達性の段階検査、親子・同壁配置の距離cache、既u128実装の再利用、余分な再検査の削減                        |
| 手の順序付け     | 全生成・全sortの代わりの段階move picker、即勝・進行・jump・壁効果の安い採点、killer/historyの保持・減衰・文脈         |
| 学習したordering | 軽い独立採点器又は小方策head、根/浅い層に限定する案。TTと併用し追加推論費と価値精度への影響を測る                     |
| 反復深化と実行   | aspiration window、PVS再探索、時計参照、次深さの見積もり、並列探索と共有TTの総費用                                    |

## 選択的探索

LMRと必要な再探索、futility、ProbCut/MPC、重要手の延長、ゴール/接触/jump/強制防御を扱う静止探索・延長、壁なし/少数壁の厳密solverを候補とする。null move等はQuoridorの手番・待ち手の性質を確かめる。浅深の誤差と戦術的取りこぼしを測り、ノード削減だけで採用しない。MPCの校正データと最終評価を分ける。

## 評価器の精度と学習

- 独立局数と局面多様性を増やした学習曲線。既存の小さい再用validationだけで十分な容量・特徴・データ量を判定しない。
- 序盤、壁配置、中盤、接触、非対称、終盤、優劣の構成と重複・露出group。量と分布の効果を区別する。
- K64教師の精度、高探索量の少数再ラベル、教師不確かさ。rootmean/rootNN/真zとαβが訪れる局面の目標・分布の整合。
- 距離の予測力を初期に保つ残差、距離場・代替経路・ボトルネック・goal到達、壁/駒の相互作用・jump/contextをNNUEへ低費用に落とす。
- 幅・深さ・活性・局面別構成、入力尺度、LR/schedule、正則化、batch、早期停止、seedを十分なデータと実行費で選ぶ。
- 小方策の補助学習とvalueへの影響、評価値の符号・校正・順位・群別誤差・実手選択を分ける。

## 評価器の実行速度

scratchの再利用、評価毎のallocation削減、深さ別accumulator stack、move由来feature差分、不要な内部局面での更新延期、距離cacheの共有、評価cacheを候補とする。量子化はfloatへの毎回復元・動的再量子化を含む総費用を確認する。AVX2/Wasm SIMD、配置・alignment・疎性・積和/reduction、tanhやlogitの計算、QAT・蒸留・大小モデルの使い分けは、対応する精度条件と同時間棋力で選ぶ。

## 教師生成・学習サイクル

常駐native推論と実GPU batch、game pool、queue、配列輸送、初期化・tail、worker負荷均衡、資源内のpipeline overlap、入力表現/mmap・学習batchを調べる。既resident GPU経路があることと現役Rust生成で実稼働することを区別する。GPU学習は明示タスクの確認済み許可・資源内だけ。

有効教師行/全job秒、局/秒、独立game/family数、全cycle費と学習・棋力への利益を測る。探索量削減や重複行増加を品質を保つ高速化と呼ばない。1000局60分、次30分は現在環境の目安であり、1000局の自動生成許可やK800品質の認定ではない。

## 検証の基準

正確性を保つ改修は同入力・同モデル・同仕事の対応と総費を確認する。探索順や近似・選択性を変える改修は戦術誤りと同時間棋力を確認する。学習候補の選定用validation、開封前にfreezeした未見評価、最終棋力対局を区別し、開封済みtestを再選定へ戻さない。173正式198局は非学習。偏った即勝盤面は能力診断層とし、拮抗・多様な色交換の主棋力層と混合しない。

Linux nativeを主にし、Wasmは必要な製品・数値・取消経路の確認。現在の距離基準を超える有用なNNUEを作る方向は維持し、理論的な期待を完成済みの実証とは扱わない。旧版の直接比較に必要なコードだけ用途と撤去条件を明示して保持する。

## 深さ6の限定perf follow-up計画

2026-10-09の人間承認は**計画のみ**。Beads `quoridor-4lc.349` に延期登録し、選択済みの深さ6・2 worker・4局throughput観測（348.2）の後に全工程費を提示して実行判断へ戻す。Sigma新時計のlive資格・D16・BEST51 NNUE16と深さ6pilotを先行させ、この後続をその依存条件にしない。旧333/337を再開せず、今はsession dispatch・worktree作成・compiler/perf/native/model実行・hardware予約を行わない。

目的は残る最適化ROIの判別であり、既に利益が尽きたとも、head/dot・FT・wallmap・TTが不足しているとも決めない。fixedDの深さ6生成に使うproduction searchと、採用済みBEST51/weights9caの深さ6production searchを別々のsource/model/rules/caller/work条件で扱う。generatorのqueue・serialization・audit費は実pilotの保存phase観測と分け、探索だけの再生をwhole生成費と呼ばない。教師・対局・fits・生成policy・既定モデルを追加変更する計画ではない。

### 一回の有限campaign案

各engineでproduction release/plain、record image/plain A0、同record image/perf P、record image/plain A1の4 process、計8 processを提案する。各processは同じ4親の完全なdepth6探索を1回ずつ実行し、計32 logical search calls（D16、NNUE16）に固定する。候補入力は348の既にtarget-blindな4 stable IDs（prefix長4/8/12/16）であり、観測後の最遅・最良局面選択をしない。実際の履歴、手番、terminal、TT4096の初期状態とプレイヤー別session、PVS、single-thread、ScalarFT/採用head、solver/order/contact OFF、depth/node/stop規則を実行前に束縛する。入力replay/setupとmodel loadは全費に含める。勝敗を進めるaction commit・game生成・teacher行保存・追加warmupを行わない。

各engine内でAction、valuebits、PV、completed depth6、stop、全23 work counters、親局面と履歴の復元を照合する。DとNNUE間の仕事は同じとは限らず、その差を速度比にしない。未達depth・error・部分結果は分母に残し、深さ6成功へ読み替えない。actual production imageとrecord imageの仕事が一致しなければ対応限界として報告し、outcomeを見てroot数・深さ・反復回数を増減しない。

sampling案は既存software cpu-clock、199Hz、DWARF stack8192B、各engine1 record、最大30 wall秒の受動的record window、各engineで少なくとも1000件の解決済みuser samplesを目標とする。sample windowが終わっても探索を中断せず、残りworkと全caller費を回収する。探索が早く終わる・window内のsampleが不足する場合は不足のまま報告し、追加record・延長・自動反復をしない。windowは探索全体の標本とは限らず、開始位置・被覆したcalls/phasesを記録する。この値は実行承認前の価格化でfreezeする候補で、今の数値実行許可ではない。install/sysctl/PMU permission probeや旧333成功suiteの再実行をしない。

### attributionと判断の限界

record buildはrelease最適化を維持したdebug/symbol情報付きimageを候補とし、実compiler/flags/build ID/ELF SHA、source、DSOとunwind方式を束縛する。debug/record buildによるcodegen/layout差は実production/plainとrecord/plainの出力・仕事・時間、必要な限定assembly対応で評価し、同じflagsだけで旧release対応を証明しない。FMA・特徴・model・探索順は変えない。Pと前後Aの全caller/plain費からperf overheadと変動を示し、補正済みCPU費や因果効果を作らない。

全sample分母、lost、unresolved、kernel/system、inline、unwindとsymbol不足を表示し、selfとinclusiveを分ける。sampleの相関・短いwindow・4親・固定順の限界を残す。旧171 sampleの割合をplain CPU費やglobal Amdahlへ転用しない。head/dot、FT delta列算術とcopy/validation/pack、wallmap/bitset、深いTT/historyその他callerを実証拠のある範囲で比較する。

成果は低影響・同意味候補と支持された条件付き利益上限、又はpoor ROI/標本不足の結論でよい。理想的なserial上限 `1/(1-f)` を示す場合も、同じplain workに適用できるfraction `f` とimage/overhead対応が支持された場合に限定し、generator throughputや実改善の予測としない。FMA、新cache/model/feature/selective searchは別scope・人間の方法選択を要する提案のまま。

### 全工程費と担当の提案

保存wholeは**3GiBの提案上限で未発行**。source64/build1536/private128/inputs32/perfdata256/raw・summary64/control64/review・Git128/TMP512/failure・cleanup288 MiBを含む。2 recordの199Hz×8192B×30秒によるstackだけの約97.8MBにmetadata/symbol情報が加わるため、perfdata256MiBを成功保証とせず実forecastを確認する。実symbol/link/build/privateサイズ・一時重なり・failed/partial保存が収まらなければ、証拠を切り捨てず具体的gapを戻す。

実時間、BEST51深さ6の費用、transient/continuous peakはUNKNOWN。8 whole processにbuild/link/symbol/preflight/model load/replay/setup/record decode/検証/report/review/Git/cleanupを足した全工程を、深さ6観測後・影響write前に価格化する。d3比率やD費からNNUE費を外挿しない。現在の保持枠39,598,288,896Bに提案3GiBを足すと42,819,514,368Bで50GB未満だが、この発行時算術はfresh free容量・grant・実peakの証明ではない。現行named supportとserial lifetimesを再照合し、旧caps/assets/failed費/RAW/masks/UNKNOWNを保持する。

将来担当はSAME探索owner `01a11004-79f3-7c20-872c-432a2c347664`、元cwd `.worktree/search-optimization`。実行許可後の専用managed worktree候補 `.worktree/depth6-focused-perf` は未作成で、作成前に保存方針を読む。sole324がMain/Git/index/resourceを扱う。practical family6GiB（controller64MiB含む）・host4GiB reserve・GPU0を候補とし、compilerは共有Cargo有限lock、numericalはsingle search threadと別physical core guardian、実topologyを確認して公平な有限intervalを使う。logical CPU数を独立core数とみなさない。

完了条件は、価格化済みの実行scopeと根拠を判断へ返すこと。後の数値実行は別途明示承認と348.2観測、source/image/input/全資源支持、full-access/never/model/effort/cwdの実context確認を要する。STOPはexact directwait/handle/process/TMP cleanupとreader releaseを保存し、binding/quiet/lock/resource/仕事の拒否やpartialを隠さず自動retryしない。必要なchanged-boundary又は重要比較結論だけを既存related reviewerへ渡し、毎run review・恒久role・定期monitorを作らない。323pause、seals、default weights、full N/4 fits/96 gateは維持する。
