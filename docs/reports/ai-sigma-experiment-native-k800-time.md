# Same-K800 native search elapsed (quoridor-4lc.180)

現在のJSON bridgeを含むRust候補は、固定Sigma-Web751186のnative-hostedJS参照よりsteady中央値で23–33%遅かった。3保存入力・各4steadyの有限測定であり、全局面の同速度／棋力／自己対局倍率やSigma C++を評価していない。

| 入力 | Rust中央値 [min,max] 秒 | JS中央値 [min,max] 秒 | C/R |
|---|---:|---:|---:|
| initial-p1 | 7.192829 [6.835621,7.969448] | 5.439503 [4.775514,5.949743] | 1.322332 |
| asym-hv-p2 | 7.406863 [7.213097,7.450866] | 5.590052 [5.404923,6.224756] | 1.325008 |
| straight-jump-p2 | 7.225083 [6.894508,8.215755] | 5.877197 [5.566991,6.076107] | 1.229342 |

実行source Git `ca7ddb93e21d26196e24db3438a2a2a86b4a7121`。結果前条件は `research-data/ai-sigma/180-native-k800-time/preregister.json`、入力は原165 saved-fiveからinitial-p1/asym-hv-p2/straight-jump-p2（0/3/7合法prefix）。原173 holdoutは使っていない。固定ONNXd790・CPUORT1.30 CPUExecutionProvider/SEQUENTIAL/intra/inter1を双方専用sessionで保持し、全processをCPU2同coreに置いた。

入力順を固定し、各入力でsession2個/startup各1を別計上→warm C,R→steady C,R,R,C,R,C,C,R。全30search完了、手NN24000/startup6、terminal-noNN0、discard0、明示NN出力cache0。非終端root初回NNbackupを1としてrootN800/edgeSum799、参照runMCTS loop799。fresh tree毎回、旧返却の再利用なし。各search60s/job480sの硬上限、科学successの補充なし。

全30のroot入力/key/history/turn/ply/features648、firstNN137bits、最終Action/合法順/訪問vector/rootmeanが参照に一致（rootmean差0）。これは有限root対応で、deep全軌跡は未保存・未確認。全30slotとwarm/steady個別値・paired ratiosはresults.json/journalに保持。

主elapsedは同controller Node monotonic時計の入力送出前から、最終CP受信parse・合法確認・root/edge数検査・structuredClone完了まで。特徴生成/合法history replay/NN/探索/輸送を含み、モデルinit/startupと保存・stopは別。402/411/500msの対局時計を持込んでいない。両外CPは最終1回、共通setImmediate event-drain/取消を保持。

固定Web本体のpolicyと研究native adapterは区別する。参照は研究browser timerをnative event drainへ置換済版をreadonly利用し、C1/FPU.2/f64/firsttie/backup/finish/合法順を変更していない。候補は既165 binary166dd0c4系を再利用し、新buildなし。原C++ GPU/batch学習経路は今回未実測・本結果で代弁しない。

| 入力 | C API sum中央値秒 | R API sum中央値秒 | C NNpipe中央値秒 | R NNpipe中央値秒 | C Rustbridge中央値秒 |
|---|---:|---:|---:|---:|---:|
|initial-p1|3.914374|4.051296|5.091776|5.138388|2.081145|
|asym-hv-p2|4.146577|4.113313|5.475696|5.299689|1.894523|
|straight-jump-p2|4.258775|4.241432|5.691216|5.569630|1.510005|

NN API spanはNN pipe spanに内包されるwallでkernelCPUへ加算変換しない。Rustbridgeはraw/new/begin800/resume800/checkpoint800/cancel/freeの計2404往復、request約0.9–1.0MB/response約7.7–8.1MB/検索。外final-onlyと内部checkpointは別で、内部root_edges構築/JSONは毎sim残る。bridge spanには小cleanupを含み、主elapsedとの厳密排他分解はしていない。cheap features/legal/BFS単独、純MCTS CPU、parse/record単独、instrumentation-free反実仮想はunknown。カウンタ/JSONbytes/NNspan/40ms監視/5秒Beads読取の計測費も現在経路に含む。

科学jobwall=196.368316秒、peak aggregate RSS=790249472B、exit0、remaining/unknown-owned空、観測TID affinity CPU2のみ。init/warm時間はresults.jsonに別記。小標本4・順序/host負荷/熱/監督CPU0の影響は完全除去未保証。主経路速度差を言語そのものの差や同K全局面の保証にしない。

NN0mockはroot4/edge3/CP1/合法/両zero/物理回収exit0。mock後の変更は入力ごとのheldsession init/close lifecycle、科学30を結果前登録。全attempt/config/source/hash/入力/command/監視/stopをpack保存。取消NN-inflightの新coverageは追加していない。

次の最大1案: CPU教師生成側Rust wrapperの毎sim checkpointをresume/beginの完了counterで置換し、最終root checkpointだけにする薄修復を別登録して同K対応と総費を確認する。NNモデル/PUCT/量を変えず内部約8MBのJSON往復を減らす候補。今回は追加測定・新teacher/game・GPU再試行なし。
