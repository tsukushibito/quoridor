# 418.1：NNUEの弱さと公開Sigmaデータの前提

対象は実arenaのfresh353 BEST43（ordered weights `046fe926`、descriptor `46ec2c47`、typed evaluator `96a5f41f`）。学習・推論・探索を新しく実行せず、保存結果と固定upstreamの一次資料を照合した。公開データが「強い現在のSigmaが作った正解集」でも「ランダム初期世代から43世代分を集めたもの」でもあるという根拠はない。データの実利用と棋力の間に複数の差があり、単独の敗因はまだ特定できない。

今回もっとも具体的に確認できた違いは、**NNUEが修正後legacyの公開勝敗を世代による重みなしで繰り返し学び、そのうちデータ番号1..20が実Tの67.9755%を占める**こと。一方、対戦相手ONNXは後のscratch321である。これは「現在の強いSigmaの値を小型ネットへ蒸留した」という構成ではない。ただし同じfix bufferからSigmaのheadsが改善した記録もあり、古いデータを捨てればNNUEが改善するという結論には至らない。

## 実BEST43への接続と、既に訂正できる読み違い

[418.2の実学習事実表](/workspaces/quoridor/.worktree/learning-million/.artifacts/research-team/nnue-premise418-facts-v1/report-ja.md)と[facts.json](/workspaces/quoridor/.worktree/learning-million/.artifacts/research-team/nnue-premise418-facts-v1/facts.json)を受領し、配布SHA/bytesを照合した。原モデル・NPZ・corpusや全学習sourceを再監査していない。実run353/job`7169a3ae`はfresh INITIAL`2ddacbf8`から始まったモデルで、旧100万行、出力bypassありBEST51/`9ca438`、固定D追加fitとは別である。

| 接続点           | 確認済みの実条件                                                                                                                                                                          | 解釈                                                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 公開観測→cache   | original9,457,039からstock不適格45,642、終了理由不明z0の156,320を除外。適格決着9,255,077をT8,413,949/V419,150/newE371,978/旧開封隔離50,000へ分割。cache`07d81abc`、元producer`cff3f550`。 | 18.9Mを全て学んだのではない。資格除外とz0除外は別理由。                                                               |
| T→fit            | epoch shuffle、uniform row loss、batch2048/tail765、T-only onlineLR50%/別RNG。世代quality・recency・game均等weightなし。                                                                  | BESTまで各original43回、361,799,807 seen、176,687 updates。反転は独立gameの倍増ではない。                             |
| 世代別の実weight | 番号1..20のTは5,719,421行、T比率0.6797546550。BESTまで245,935,103 row露出。                                                                                                               | 「初期20世代が弱い」という測定ではなく、**古い番号の行が損失の約68%を占める**という確認。                             |
| 特徴→出力        | QF1二つの312 view、FT32/H32 ReLU、Zero4、T-only標準化した二距離D/80、final tanh。固定OUTPUT a=b=0。                                                                                       | distanceを除いたモデルではない。Sigmaの全距離map入力、大CNN、policy/value jointとは異なる。                           |
| BEST選択         | 開封Vのrow MSE最小がepoch43、0.42387071217019406。最後の有意改善38から8 staleの46で停止、strict43はpatienceをresetしない。                                                                | 43は公開shard数やSigmaのcycle番号ではない。LR/early stopによる一般収束・棋力最良の証明ではない。                      |
| Python→native    | 12,321 LE-f32/49,284B、同046fe/46ec/96a5が現在417 source bindingにも指定される。既存BEST/LAST CPU/CUDA四batch/16row・四prefixで有限対応、max7.45e-8、delta-full2.086e-7。                 | 大きい符号/scale/export取り違えを支持する証拠は今回ない。全state/current imageの再資格や417 runtime結果は主張しない。 |

STMはcanonical player0/own goal row8、opponent view180度。正しいonlineLRはpawn x→8−x、wall anchor x→7−xで、z・STM・stocks・距離を保持する。公開の旧naiveLR半分は今回の訓練対象ではない。既知の古い変換問題を、修正後BEST43の直接原因として残してはならない。

splitはblob+originalrowの固定分割で、game分割ではない。LR兄弟同splitは確認されるが、別originalに同じモデル入力・別zがあれば保持される。T distinct1,819,065/V185,666は入力数で、歴史的`game_equal`という欄も実際には入力group均等metric。旧開封50,000の元ID隔離は同盤面・同gameの完全非露出を保証しない。開封Vはschedule/BESTの選定集合であり、独立sealed評価ではない。

BESTのtrain MSE0.42658014263409844は**固定8192行の診断**で、fullTではない。fullTはepoch1と5刻みの保存点のみである。Vの0.4238707とこの診断値の近さだけから「過学習なし」「容量不足」「全trainを学び切った」を判定できない。V sign84.3113%、group MSE0.3904731とrow MSE0.4238707も異なる重みの指標。保存saturation48.5397%は`|v|>=0.9`の割合で、0.99への飽和や勾配消失の割合ではない。旧BEST51の大きな残差や個別飽和例をBEST43の実観測へ移さない。

## 公開データの来歴で訂正すべき前提

| 問い                               | 確認できたこと                                                                                                                                                                                              | 残る限界                                                                                                                                                               |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 公開43とは何か                     | 固定`751186344fc52ad0c29bc65922e62c6fa915f006`の`runs/data_9x9_fix/cycle_0001..0043.npz`。保存18,914,078行、original9,457,039行。                                                                           | 全学習史・43 checkpointの棋力・独立game数ではない。                                                                                                                    |
| 最初の0001は未学習モデルか         | 43番追加時の`84cfb8d311c5a6ebd853fcb28cc713e54434b925`のloopは`models_9x9/best.pt`から`data_9x9_fix`へ生成。固定head改修記録は既学習legacy cycle359と修正後bufferを対応させ、継続方策修正だったと説明する。 | 0001の生成重みSHAは未特定。データ番号をモデル学習cycleへ直接置換できない。                                                                                             |
| 方策修正前の全データが混じるか     | `4f418e4b`（2026-07-19）はreversed-policy修正、`ce20f4a1`は旧データ削除、`84cfb8d3`で43番まで公開。`ce20`のfix1..20は固定版と全20 blob一致、`84cf`時点でfix43も固定版と一致。                               | コミットメッセージは実生成実行の完全なmanifestではない。「修正前の全履歴を混在」と断定できない一方、各観測の生成時にどの実行コードを使ったかも完全には再構成できない。 |
| 公開43は対戦相手ONNXの生成データか | `a7a91e5e`（2026-07-25）の原作者履歴はbrowser bestをscratch321へ交換したと明記。固定`docs/models_9x9/best.onnx`はblob`f23802a8…`、11,663,428Bで既保持arena参照と対応する。                                  | fix43は別のlegacy/heads経路である。ONNXの強さをfix各世代へ転写できない。モデル本体の再取得・再hash・forwardはしていない。                                              |
| 古いfixデータは役に立たないか      | head改修記録は同じfix bufferでwarm-startしたheadsを教師学習し、legacy359に63.9%のscore（1024局、800sim）だったと報告している。                                                                              | 原作者の別モデル・policy/value joint・warm trunk・別探索の結果。NNUEへの有効性や因果効果を直接示さないが、「このbufferでは強くなれない」という断定への反証材料になる。 |

原参照は[固定head改修記録](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/markdown_notes/HEAD_REDESIGN_PLAN.md)、[43番追加時のloop](https://github.com/bartolomeo3000/SigmaQuoridor/blob/84cfb8d311c5a6ebd853fcb28cc713e54434b925/cpp_train_loop.py)、[ONNX交換commit](https://github.com/bartolomeo3000/SigmaQuoridor/commit/a7a91e5e8ccb561b9e520bc96a1c199a0f16ab12)。私有`upstream-historical-data-trees.json`、`upstream-data-blob-continuity.json`、`upstream-selected-tree.json`にAPI URLとblob対応を保存した。親treeに一致blobが無いfirst5を、破損・改変・旧cycle由来と推測しない。

`models_9x9/training_stats.csv`はcycle340..382の43行を含み、後述の30/.92を記録する。fix1..43との「339ずれ」は個数上整合する候補だが、各ファイルを対応させる生成receiptがないため採用しない。固定treeに公開`runs/logs/`の実ファイルはなく、NPZに生成checkpoint hash・game ID・完全historyを保存する経路も確認できない。`plies_to_end`のsource保存機能があることと、今回の全43にその列が存在しgame境界を復元できることを同一視しない。今回NPZを開いていない。

## SigmaのreplayとNNUEの全量学習は同じ操作ではない

固定READMEは直近30 cycleを説明するが、同じ固定revisionの`train.py`実defaultは60、recency decay0.99である。これは後期PCR経路の変更で、fixed READMEだけから実run設定は決まらない。43番追加時のhistorical`84cf`ではdefault30/.92、固定legacy CSVの340..382でも30/.92。head改修記録では30/.92から一時的に50/1.0へ切り替えて全bufferを使い、最後に30/.92へ戻している。したがって「Sigmaは一貫して古いデータを捨てた」も「Sigma自身も43ファイルを一様なepochで学習した」も不正確である。

実sourceのreplayは最も新しいKファイルを保持し、ファイル内の各行へ`decay ** age`を与え、正規化して**復元抽出**する。世代ごとの総抽出率は`行数 × decay ** age`に比例し、各世代同率ではない。古いcycleの累積生涯exposureは、そのcycle以降の各training phaseのsamplingを足した量なので、最後のbuffer重みだけでは分からない。NNUEの固定全量epochとの比較では、この差を保つ。[固定train.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/train.py)のReplayBuffer、run_training_phase、load_buffer_from_disk、[歴史版](https://github.com/bartolomeo3000/SigmaQuoridor/blob/84cfb8d311c5a6ebd853fcb28cc713e54434b925/train.py)を根拠とする。

保存headerだけから得たoriginal観測数は以下。これは除外・split前であり実BEST43のT内率ではない。

| データ番号 | original行 | 全original比率 |
| ---------- | ---------: | -------------: |
| 1..10      |  3,164,150 |       33.4581% |
| 11..20     |  3,267,499 |       34.5510% |
| 21..30     |  1,263,023 |       13.3554% |
| 31..43     |  1,762,367 |       18.6355% |

前半1..20が6,431,649行、68.0091%を占める。均等row学習なら多数行の世代・繰り返す局面・長いgameが大きな重みを持つ。これは弱い世代が68%という意味ではなく、各世代の強さは未測定。途中の行数減少をゲーム数変更・短期決着・solver・間引きのいずれかに、receiptなしで帰属しない。

同じraw行数へsourceのsampling式だけを適用する**算術例**では、43番時点の30/.92 kernelが1..20へ与える総確率は15.7467%（1..13は窓外）、60/.99なら63.1332%、全43均等rowなら68.0091%になる。`weighting-illustration.json`に式・分母を保存した。これはsourceの意味を示す反実仮想で、実T割合、過去Sigmaの累積exposure、各世代の強さや棋力への効果を測ったものではない。

## 教師zの意味と、探索で欲しい値の差

upstreamは着手前のcanonical STM局面とpolicyを記録し、終局時に記録手番がwinnerなら+1、相手なら−1、winnerなしなら0を割り当てる。zは実続行の結果であり、raw NN valueでもMCTS root meanでも最適WDLでもない。MCTS policy targetはvisit分布で、別のheadをjointに学習する。NNUEのz回帰にはそのpolicy headの知識が直接渡っていない。[固定selfplay.hpp](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/selfplay.hpp)のplay_move/finalize_game、[train.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/train.py)のcompute_lossを参照。

弱い方策の実勝敗も、その方策下の正しい観測であり、同じ入力で±1が混じること自体は破損を意味しない。方策の確率性、対局相手、生成世代、NNに見えないhistory等が違えば結果は変わる。row重み付きMSEの理想回帰先は、入力Xと採用条件に条件付けたその混合分布での`E[z | X, 採用]`である。αβのmin/maxが欲しい一貫した強い続行値と同じである保証はない。ただしこれは一般的な意味の差であり、MCTS由来zがαβ教師に不適切だと証明したものでもない。

z0を除くと、ほかの条件を同じとした理想目標は`(p_win - p_loss)/(p_win + p_loss)`になる。無条件の`p_win - p_loss`や引分込み期待scoreとは違う。今回の0は終了理由不明なので引分の真値として再投入する根拠もない。除外は既知の保守的処理で、その選択による校正差を残す。native資格除外・観測split・入力圧縮も条件を加える。

root solverが返した完全終局続行の局面は、その限定history/rules下で強い終局情報を持ち得る。しかし上流の中盤局面まで最適だったことにはならない。固定sourceのroot solver default1・PCR25%記録・max160等を全public43へ移さない。43番公開時のloop defaultはroot solver2、800sim、temperature0.8→0.15/halflife6、max160、noise0.3/.25、FPU.1、9x9/10壁で、PCR設定はまだない。これは**そのsourceの既定値**であり実各shardのCLI/solver成功率・打切り理由のmanifestではない。

## 実敗戦・比較が支持するところと、支持しないところ

既存355の同時間比較ではBEST43の対D goalは87/256、358の完成深さ4比較では98勝・157敗・1引分、half-draw score98.5/256=38.4766%。元の128 full-history families/両色/当時のimageと規約の有限結果で、現在設定の普遍棋力へ拡張しない。同深さでも劣位なので、**評価が遅く深く読めないことだけ**では当時の差を説明しきれない。ただし同深さが最適値・同じ探索木・同じleaf分布を意味するわけでもない。[比較の保存解釈](/workspaces/quoridor/docs/research-findings.md:818)を再用した。

383の保存敗戦12局は、各相手ごとの先頭6敗戦という後付け選択である。高いsearched-root値と浅いdepth3の後、壁と相手応手で自分の迂回が伸びる例がある。D slot4/ply39では双方残壁1、距離16/4、depth5/root+0.99928635から、ply41のdepth9/+0.12373722、ply43のdepth10/−1へ変わる。これは浅い序盤だけでなく低壁数・長い迂回の見通しも調べる材料。ただし**root値は静的NN出力ではない**ので、保存曲線の0.9飽和とこの+0.9993をつないで「NNUE飽和が原因」とは言えない。別手で救えたか、最初の誤りはどこか、その局面の最適WDLも未確定。[383の元報告](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/report-ja.md)の確認済み範囲を[統合findings](/workspaces/quoridor/docs/research-findings.md:1419)から読んだ。

415は同じ評価器内のLMR A/B比較で、NNUE対Dではない。全98pairで分岐し、Bが最初の分岐で深かったのはNNUE/Dそれぞれ1件、NNUE97完成比較のroot値は全て異なる。これは探索選択と静的評価を分離して調べる必要を示すが、旧公開データやNNUE単体の誤りを示すoracleではない。[415元報告](/workspaces/quoridor/research-data/ai-sigma/lmr-game-analysis415/report-ja.md)。進行417の枝比較をこのデータ分析の結果へ先取りせず、元383/415のRAW再抽出・盤面再生・新Searchは行っていない。

## 競合原因と最小の識別材料

| 優先して分ける問い                                  | 今回の証拠                                                                                                 | 反証・交絡                                                                                                     | 次に一つだけ確認するなら（未実行の提案）                                                                                                                             |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 世代・方策mixと採用重みが探索の欲しい値からずれるか | 公開fixと相手scratchは別lineage。実Tの1..20への67.98%集中、Sigmaのrecency/rolling処理との違い。            | fixは未学習初期データとは限らず、同bufferはheads強化にも使われた。古い世代の悪影響は未測定。                   | 実T割合は今回確定。古いデータの悪影響を識別するなら同じモデル/更新予算/固定評価で世代weightだけ変える対照が必要。coverage変化も伴うのでqualityの単独効果にはしない。 |
| 学習軌跡とαβで選ばれる葉の分布が違うか              | 勝敗回帰が教師方策の続行を予測するのに対し、αβは候補葉の極値を選ぶ。固定深さ4比較でもBEST43はDに負け越す。 | min/maxが誤差を強調することは機序候補。実失敗でどのleaf誤差が採用手を変えたかは未測定。                        | 既存BEST43敗戦の一つで、同じhistory・完成深さ・候補手を揃えた有限leaf/action比較。深いD/Sigmaをoracleにはしない。                                                    |
| 表現・容量・最適化に原因があるか                    | 小NNUEの二視点QF1+distanceとSigmaの大きいCNN/policy-value jointは違う。MSE改善と棋力一致は保証されない。   | 過去小subsetの過学習、BEST51の飽和例をBEST43へ直接移せない。train loss残存だけで容量不足は決まらない。         | BEST43保存曲線と同一入力別zの既存noise情報を対応させ、bias・variance・最適化のどれまで識別可能か限定する。                                                           |
| ラベル・座標・native接続の不具合か                  | old naiveLR問題は既知で、original再抽出とonlineLR修正の経路が用意された。符号はSTMの契約で整合。           | 既存有限parityは全分布の証明ではない。一方、古いnaiveLRを現在BEST43の直接原因とするのも誤り。                  | 実BEST43→実供給cache→nativeのmanifest/FileRef連鎖に欠落があれば、その一点を保存証拠で補う。成功suiteの再演は不要。                                                   |
| 観測splitと反復状態がvalidationを易しくするか       | distinct入力数は観測数より少なく、game/historyが欠ける。反転兄弟同splitは独立game splitと別。              | 同入力別結果は合法な確率変動。V漏れが弱さを生むという単純因果ではなく、主に選定指標の解釈の問題。              | 既存split方式・既開封範囲・同入力のsplit横断情報で、Vが評価する母集団を明示。sealed/newEを開かない。                                                                 |
| 同時間探索費・TT/LMRが弱さを増幅するか              | 415のNNUE/固定Dは別軌跡で探索深度分布も違う。旧TT非対称比較がある。                                        | 固定深さ4でも負け越すので速度差だけが全原因ではない。415は同じ評価器内のLMR比較で、NNUE対Dの棋力比較ではない。 | 既存同深さ結果と同時間結果を別々に読む。進行417のLMR観測はLMRの問いとして維持する。                                                                                  |

この順位は識別のための優先度で、原因確率の推定ではない。最新世代だけへの切替、全量廃棄、ラベル再付与、特徴変更、fit再開を今回の分析から自動採用しない。短期的には「強いSigmaから移植すればNNUEも同じ強さになる」「MSEがSigmaより小さければ対局も強い」「全量の行数が多ければ独立な良質サンプルが多い」という推論を外すのが先である。

## 証拠の範囲と継続

固定版のsource・小さいCSV・原作者notes・GitHub tree/commit metadataのみ外部から読んだ。HTTP404（誤候補`cpp_selfplay.py`、存在しない`models_9x9_fix/training_stats.csv`、`docs/models.json`）はrefsに残す。全repo/model/dependency/NPZのdownloadは0、全NPZ decode/hash、forward、fit、Search、arena、solver、build、test、新bootstrap、sealed/newE label開封は0。Git/index/Mainは変更していない。

418.2受領後に実BEST43のモデル・供給・native連鎖と実曲線を統合し、今回許可されたread-only分析を完成した。重要な単独原因の確定は0で、解けない生成checkpoint/game/history/棋力効果はUNKNOWNのまま保持する。旧mixed/learner全prep/pipelineおよび323はUSERPAUSEのまま。元RAW/FAILED/費用/UNKNOWNを変更しない。decimal50GB上限、保守上界49,278,775,296B、global actual UNKNOWNを保持する。

`verification.json`はcompact418.2の受領前後SHA、ローカル43-file manifestと固定公開treeのblob/size一致、全43が公開時84cfと固定751186で同blob、original/split/epoch露出の小算術を確認する。NPZ本体を再hashした結果ではない。手書き`guard.py`/`verify.py`へ既存Ruff format/check/lint、報告へ既存Prettier write/checkを限定適用した。最初のPrettier呼出しはignore設定で対象を処理しておらず、`--ignore-path /dev/null`による実整形と確認へ訂正し、原receiptを残した。

通常source/小算術/formatterはCPU8(core4)、guardian12(core6)、child family960MiB＋guardian余裕64MiB、host reserve4GiB、GPU0の既存guard。Root/324の配置確認後、417 actual timing holdは今回届いておらず、そのsource準備と並行した。全bounded commandの直接wait/reap、tracked PID/start/bootのfresh不在、handle閉鎖、TMP/owned[]を最終`STOP.json`に保存する。初期設定・管理command・LLMを含む全費およびcontinuous family peakはUNKNOWN。guard費を元科学run費や内側command費と二重加算せず、今回の一度の対象usageは`usage.json`に記録する。

Main/findingsへの出版と親418の受入れは324が行う。今回の結果は前提の訂正と仮説の識別可能性であり、NNUEの新棋力資格・新データ生成・paused学習の再開を与えない。
