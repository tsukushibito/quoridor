# ルール・局面・履歴

公開入口は[src/lib.rs](src/lib.rs)の`Position`/`Action`/`Game`。局面と合法手は[position.rs](src/position.rs)、replay/undoと画面用viewは[game.rs](src/game.rs)へ進む。

研究用`SigmaContext`と履歴・壁距離map・play/undoは[research.rs](src/research.rs)（`research` feature）。完全な距離mapの内部再用と、NNUEへ渡す特徴を混同しない。QF1入力の責務は[NNUE crate](../quoridor-nnue/README.md)にある。

検証の入口は[ルール](tests/rules.rs)、[文脈の復帰](tests/context_undo.rs)、[距離queue](tests/fixed_queue.rs)。プロファイルは[profiling.rs](src/profiling.rs)と対応testを参照する。`cargo test -p quoridor-core --features research`はcompileを伴うルール検証で、学習や対局ではない。

探索は[ai](../quoridor-ai/README.md)、ブラウザの型/シリアライズは[wasm](../quoridor-wasm/README.md)。crateへissue・期限・CPU番号を埋め込まず、実行側configで束縛する。
