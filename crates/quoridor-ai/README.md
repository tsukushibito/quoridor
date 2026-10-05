# 探索と評価器の境界

[src/lib.rs](src/lib.rs)は公開探索型と基本PUCT。native研究のαβ/PVS・反復深化・TT・ordering・取消/期限は[alphabeta.rs](src/alphabeta.rs)、Sigma型MCTSは[sigma_mcts.rs](src/sigma_mcts.rs)へ進む（`research` feature）。

αβの距離/NNUE評価器と探索limitsを分けて調べる。NNUE重み・特徴は[NNUE crate](../quoridor-nnue/README.md)、合法手・履歴は[core](../quoridor-core/README.md)。MCTSの推論要求を実providerへ束ねる実行管理は[runner](../quoridor-runner/README.md)と[inference](../quoridor-inference/README.md)の責務。ここからPython/旧Node/過去frameの管理scriptを呼ばない。

[探索test](tests/search.rs)と[αβ test](tests/alphabeta_search.rs)が合法性・視点・終局・時間/取消の検証入口。`cargo test -p quoridor-ai --features research`はcompileと合成fixture検証。実モデルの費測定、生成、同時間対局は[運用手順](../../docs/development/rust-ai.md)で別に実施し、速度だけで棋力を認定しない。
