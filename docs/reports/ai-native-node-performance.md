# Linux releaseと保全Node版の実速度比較

Beads `quoridor-8lp`。Linux releaseは同じCPU条件の保全Node版より今回の3局面で短時間だった。NNUEの評価演算は約13倍、深さ2のαβ探索は約1.4–2.7倍、同K800/CPU ORTのMCTSは約1.15–1.18倍。局面、モデル、探索量、費用範囲を下記のように固定した有限測定であり、全局面・深い探索・全生成・棋力の改善率ではない。

## 比較条件

- Nodeの現役保全入口は `tools/ai-sigma-native/{nnue,search,reference}.cjs`。Rustはproduction crate APIをrelease exampleから呼び出した。旧製品B0 AIとの比較ではない。
- Linux x86_64、Rust1.98.1/Node24.21.0。同じphysical core2へpinし、同時に探索しない。ホストのphysical core16/18とRAM4GiBをreserve、native admissionの上限2GiB。GPUは使っていない。
- 初期P1、pawn-step後P2、horizontal-wall後P2の合法prefix `[]/[13]/[107]`。モデルロード・局面再生・要求解析・応答JSON化はsteady測定外。重み/sessionは常駐、測定順を毎round交替。
- NNUEは同じQF1-H32学生重みSHA `c0c0f021e9c092c225d1e4eeea156a712d41dec4cc3dce6f4b4930a0b98e60d3`。学習や重み採用の変更なし。
- MCTSは同Sigma ONNX SHA `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d`、ORT1.30.0 CPU、intra/inter1、SEQUENTIAL、graph optimization ALL、batch1。K800/root800/NN800、同合法順・探索規則。
- eval/searchは各variant・局面でwarm1/steady5、MCTSはwarm1/steady3。最終正本run-r2は132応答/24MCTS検索、全19200NN。run-r1は整形前の同試験として別保存し、データを混合しない。

## NNUE評価演算

準備済みaccumulatorから5000回のnetwork評価。特徴抽出、距離/BFS、accumulator構築、差分更新は含めない。両側の値と和を観測し、最適化で評価loopを除去しない。

| 局面 | Node 5000評価 | Rust scalar | Node/Rust |
| --- | ---: | ---: | ---: |
| initial-p1 | 37.378ms | 2.924ms | 12.78 |
| pawn-step-p2 | 35.343ms | 2.567ms | 13.77 |
| horizontal-wall-p2 | 39.269ms | 2.944ms | 13.34 |

全準備済み評価値がexact一致。Rust SIMDも別測定し、約13–14倍の範囲でscalarと大きな差は出ていない。小さいH32で、このfixtureの演算に対する結果に限る。

## 深さ2を完了するαβ探索

同じNNUE評価器、反復深化で深さ1/2を完成、node cap100万、時間打切りなし。全測定でActionとvalueがexact一致。探索から最終合法性確認までを含み、モデルロードとroot再生は含めない。

| 局面 | Node中央値 | Rust scalar中央値 | Node/Rust | Node/Rust探索nodes |
| --- | ---: | ---: | ---: | ---: |
| initial-p1 | 31.434ms | 19.574ms | 1.61 | 530/530 |
| pawn-step-p2 | 23.193ms | 16.511ms | 1.40 | 657/660 |
| horizontal-wall-p2 | 44.120ms | 16.351ms | 2.70 | 1217/779 |

RustにはPVS/TT/killer/history、Nodeには従来のrootbest orderingと区間計測がある。nodes/evaluationsが異なるため、同じ深さの完成に要した時間であり、言語だけの倍率ではない。全合法手を対象とするが、全子のexact値を別々に保存した比較ではない。fixtureには深さ2内の終局がなく、終局score conventionの差をこの時間比へ混ぜていない。SIMDの深さ2結果も別保存し、今回の範囲ではscalarからの一貫した速度利益は観測していない。

## 同モデル・同K800のMCTS

| 局面 | Node中央値 | Rust中央値 | Node/Rust |
| --- | ---: | ---: | ---: |
| initial-p1 | 3.595s | 3.082s | 1.167 |
| pawn-step-p2 | 3.551s | 3.078s | 1.154 |
| horizontal-wall-p2 | 3.573s | 3.029s | 1.180 |

全24応答でAction、rootmean、root800、NN800、全edge訪問/valueSumがexact一致。Nodeは既存の常駐Python ORT JSONL provider、Rustはin-process ORTなので、探索・入力構築・輸送/serialization・CPU推論を含む現在経路の差である。Nodeは保全portStateとreference wrapperの費用を含み、純MCTS数理部分やRust言語単体の速度比ではない。

Rustのinfer呼出し時間は検索の大半で、CPU NNが支配的。約13倍のNNUE小network演算差をSigma MCTSへ読み替えない。GPUのgeneration/CUDA Graph/TensorRT/Arrow全保存や同時間棋力はこの測定対象外。

## 保存・再現・検証

`tools/ai-native-node-benchmark/README.md` に入口、`crates/quoridor-runner/examples/node_comparison.rs` にproduction API呼出しを置いた。計測の唯一writerはroot/main。既存model/env、保全Nodeコード、旧科学結果、研究schedulerは変更しない。

正本は `research-data/ai-sigma/native-node-performance/run-r2/{plan,readiness,summary,stop}.json` と `raw.jsonl.gz`。全132recordの値/Action、全MCTS edge/countersを再算し、両process exit0/wait、gzip全byte復元を確認。SHA付き `verification.json` は測定源とデータに束縛する。run-r1も別保存。初回exampleのAPI名/boxed error型のbuild不足はモデル実行前に修復し、productionのアルゴリズムは変更していない。

最終Rust example release build/Clippy、Rustfmt、Node構文/Prettier、Python Ruff lint/formatが成功。最終モデル測定sourceは整形後に固定し、run-r2中の書換えなし。モデルとbuildはGitへ追加せず、設定・原応答・小報告のみを保存する。
