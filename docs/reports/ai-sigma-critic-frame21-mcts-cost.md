# frame21 MCTS固定root費用 / quoridor-4lc.271

4登録root・各K64・CPU ORT単スレッドの一回profileで、root処理の99.0858%が推論API区間だった。旧267 candidate sample0のAction、rootmean bits、全edge policy/visit/value hash、features、合法手、nodes/NNは4rootとも完全一致。core/ai/inference/pumpを変更せず、新一般用途exampleだけで測定した。

| 排他区間                        | 4root合計ms | root処理比 |
| ------------------------------- | ----------: | ---------: |
| setup（prefix再構成・tree作成） |    0.314420 |    0.0322% |
| advance                         |    2.626605 |    0.2690% |
| infer                           |  967.406801 |   99.0858% |
| supply                          |    5.905861 |    0.6049% |
| loop/timer未帰属                |    0.078402 |    0.0080% |
| root処理全体                    |  976.332089 |       100% |

advance内部の特徴・合法・探索別内訳は測っていない。inferは入力検査/FFI/ORT/outputを含むAPI区間で、operator/kernel排他費とは主張しない。supplyにはtree展開が入る。snapshot・資格確認・出力はroot timer外でwholejobに入る。

ORT初期化39.761164ms、wholejob1017.541797ms、guardian1.046819338秒。compile7.099800638秒を別計上。全science一回、256NN、30,856 allocated tree nodes、peak RSS55,648,256B。上界NN10000/processed50000/MAX1/hard45s、compile120秒内。完了4root/root64edge63、terminal-noNN0。cold先頭を含む順序固定・単試行で速度分布や全生成倍率を認定しない。

次最大1案は、既存モデルの常駐GPU/batch backendを独立treeのnative MCTS pumpへつなぐ一介入。現CPU ORTのbatch APIはnative内でbatch1逐次Runなので、要求をまとめるだけの高速化とはしない。同K・ID対応・有限root資格を保ち、有効教師行/初期化・輸送・記録・回収込み全job秒と実装検証費で選ぶ。今回GPU比較・game生成・fullgame Rjoint・棋力は未測定で、推論区間優勢だけでGPU利益を保証しない。

## 版・実行・保存

- WT `/workspaces/quoridor/.worktree/frame21-search`、base `ca7522195dfb8a9b60fabee3022825045074620b`。Git/index操作は統括だけ。
- core SHA `a12641610b25fd7bb36b7a3408ed377fdb9c4767e6e5f2edbd792090686c7736`、新example SHA `7935af7a7e13a6260a7bea5b83b7749839b437b33f4ccf9d4ab109bd95513636`。
- task `frame21-mcts-cost-271-v1`、schema `mcts-cost-v1`。preregister/config・専用argv/binarySHAは自域に保存。held ONNX `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d`、ORT1.30.0。generation1979はRNG seedとは呼ばない。ORT_DISABLE_TELEMETRY=1。
- profile 2026-10-05 10:20:01.205937→10:20:02.252741 UTC。compile/profile exit0、全child wait/current exact不在。科学source停止はscience-stop.json。fresh loaded scheduler/monitor PIDtick/current24/CPU/RAMは各admission点、全期間/全host不在保証ではない。
- aggregate基準は92 directed admission09:46、入口で旧scope・sharedrelease実量/forecastを確認。全retained roots後点再計上12,138,590,208B/errors0は入口全root再計測の代用ではない。unknown旧128MiBと旧管理予約を保持し、新1MiBは267旧4MiBから移転、旧3MiBはcurrent589824+Git/tmp1048576=1638400B以内。
- Rust rustfmt/check、専用Python Ruff format/check、config Prettier write/check。凍結267 source/dataに再整形なし。NN0 check_saved.pyで保存算術と旧root一致を再構成できる。

再現（新science起動は現在/将来の個別配分条件に従う）:

```bash
source /workspaces/quoridor/scripts/dev/project-env.sh
taskset -c 2 /workspaces/quoridor/.artifacts/rust-migration/target/release/examples/mcts_cost research-data/ai-sigma/frame21-mcts-cost/config.json
python3 research-data/ai-sigma/frame21-mcts-cost/check_saved.py
```

science出力・失敗なし全attempt・preregister/admission/process・sourceSHA・pack member復元を保持。旧267のMAX/費と旧test/173は変更・読取なし。統括へpatch/new exampleと停止版を引渡し、main統合は別判断。最高棋力goal未達。

## 統括source追補への次案補正

現runtimeは既にpending/config/backendの上限と2ms fillでpumpbatchしている。CPUのinfer(&4)追加や「GPUへ新たに接続」を次介入として扱わない。TensorRT nativeはbatch別の形状/context/device・host buffersを保持しenqueue/graph経路を持つが、このsourceだけで現GPUの速度・実batch分布を認定しない。

次最大1は、既存常駐TensorRT graph教師pumpで同model/K64/worker/maxB8/2ms fillを保持したactive-games24対48の一介入。同全予定仕事量で実batch histogram・queue/fill待ち・infer・startup/capture・tailと適格Rjoint/全job秒を併記し、並列tree供給不足が実推論費を減らす余地を選ぶ。取得/新モデル変換を含めず、使用可能な既package/model/runtimeのbindingと有限数値/ID/教師境界を先に登録する。batch順で乱数や探索が変われば差を保存し同品質を自動認定しない。既に十分batchが満ちている場合の無利益も保持する。新runは今回行わず、GPU利益/全生成倍率/将来費用回収は未知。
