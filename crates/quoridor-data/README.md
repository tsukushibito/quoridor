# 教師データと学習入力

公開入口は[src/lib.rs](src/lib.rs)。`TeacherRow`/`Teacher`/`Split`がschemaと視点・game/family/lineage・教師種別を表す。MCTS rootmean、αβ値と証明済みterminal、真のzを暗黙に混ぜない。

`DatasetWriter`/`write_dataset`はArrow shard、`read_dataset`/`for_each_row`は保持された入力の読取、`write_tensor_cache`は学習用mmap tensorへ進む入口。splitと露出判定を保持し、sealed test読取は明示許可を要求する。教師生成は[runner](../quoridor-runner/README.md)、学習は[Python package](../../python/quoridor_training/README.md)にある。

契約検証は[tests/datasets.rs](tests/datasets.rs)。`cargo test -p quoridor-data`はcompileと合成データ検証で、既datasetの学習/全展開ではない。実データ操作は[学習手順](../../docs/development/nnue-training.md)と[保存境界](../../research-data/README.md)を使う。過去ラベル・split・科学結果をコード移行で書き換えない。
