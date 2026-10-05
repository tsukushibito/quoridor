# Rust AI移行の実装検証

対象: Beads `quoridor-cyo`。設計は[Rust移行設計](../design/ai-rust-migration.md)、実行手順は[運用手順](../development/rust-ai.md)。Linuxネイティブを評価・探索・推論・生成・学習cycleの主経路とし、WasmはCPU評価・探索を利用する製品経路の一つとする。

## 実装した境界

| crate / module | 責務 |
| --- | --- |
| `quoridor-core` | 合法手、繰り返し履歴、距離、研究用make/unmake |
| `quoridor-nnue` | QF1二視点疎特徴、共有重み、差分accumulator、float SIMD、量子化評価、checksum検証 |
| `quoridor-ai` | NNUE/距離評価の反復深化αβ/PVS、TT、killer/history、任意ordering接口、Sigma対応typed MCTS |
| `quoridor-inference` | 常駐CPU ORT / CUDA AOTI / TensorRT、native SDK adapter、部分batch、CUDA Graph、入出力/版/SHA検査 |
| `quoridor-data` | 圧縮Arrow shard、教師方式・WDLの分離、family split、露出mask、bulk特徴cache |
| `quoridor-runner` | multi-game worker、1木1pendingの推論broker、取消/回収、Linux資源admission、生成・対局・cycle CLI |
| `quoridor-wasm` | 同じCPU NNUE/探索のWorker向けAPI、完了深度通知、scalar/SIMD artifact |

Python/PyTorchは学習・曲線・解析・モデル変換を担当する。探索ノードやNN leafのhot pathにはPython、JSON、外部process往復を置かない。モデル変換のPythonとnative SDKのC/C++ shimは、この分担の外部依存境界である。旧JS/Rust bridgeは独立互換性oracleと歴史runの再現用に保持する。

## Linuxの実動作

固定Sigmaルール/探索のtyped MCTSを、独立JS oracleと3合法入力×K32/64/800で比較した。離散Action、訪問数、NN要求数、root値/ledgerに対応を確認した。これは決定的合成NNでの機構検証であり、全局面の棋力同等判定ではない。

NNUEは全合法子のfull/delta/undo、float scalar/SIMD、量子化・overflow拒否、破損manifest拒否を検査した。αβはTT/PVSと無効化時の対応、終局値の優先、反復深化の完成深度、取消・評価例外後のroot復元、orderingが合法手を削除しないことを検査した。選択的枝刈りをこの移行で実証したとはしない。

実際にPyTorchから出力した学生重みをLinux release runnerで再読込し、testの111行をSIMD評価した。PyTorch予測との差は最大 `4.470348358e-8`、平均 `1.342446954e-8`。手続き上freeze後にtestを開き、設定選択へ戻していない。

CPUの小cycleでは12局/650適格行を生成、10step/3975sampleの学習、checkpoint/モデル/ONNX出力、freeze、test、native arenaへの接続を実行した。独立したrelease arenaは同凍結重み/100msで4予定局が全GOAL、学生0勝4敗。モデルは採用していない。最初のdebug 10ms arenaの3未完了は別に保存し、release結果で置換していない。

修復後のGPU一括cycle r2は、MCTS/TensorRTの8局/446適格行を10.348731秒で生成し、10step/2885sampleを0.962297秒で学習した。候補freeze後に未見2局/125行を一度開き、同じCLIからrelease SIMD/100msの4局arenaまで全GOALで完了した。testの学生局等重みMSE `.563499` は距離基準 `.307304` に届かず、arenaも0勝4敗、採用receiptはfalse。短い機能検証の学習量・局数であり、学習能力や棋力の最終判定ではない。

このGPU cycleで出力した実学生モデルの125行も、凍結PyTorch予測とLinux SIMD評価を比較し、最大差 `5.2154e-8` を確認した。

## Native CPU/GPU生成の実費

同じ新8局の入力/seed、K32、固定Sigmaモデル、worker core2/4、推論owner core6、maxB8で実行した。各backendは常駐し、生成時間はbackend初期化から記録・worker回収までを含む。全8局GOAL、446適格行、12802 NN、全Action列/勝者/手数/NN数が保存結果で一致した。

| native backend | 全生成秒 | 推論呼出し区間秒 | 適格行/秒 | peak RSS |
| --- | ---: | ---: | ---: | ---: |
| CPU ORT | 57.604253 | 51.208068 | 7.7425 | 653,275,136 B |
| TensorRT GPU | 11.337379 | 3.550728 | 39.3389 | 878,723,072 B |

この全生成の点推定はGPUが約5.08倍。固定順の単回・単一ホスト・8局で、batch分布やhost負荷が少し異なる。将来の大規模生成倍率・棋力・純kernel倍率の保証ではない。取消/EOF/typed faultを含む全予定slotを結果に残し、未完了を教師ゼロへ変換しない。

別の固定24合法入力によるbackend数値検証はB1/2/3/5/6/7/8/16/24を実行した。CPU ORT対CUDA AOTIの最大差 `9.54e-6`、TensorRT `4.53e-6`、登録tol `abs1e-4+rel1e-4` 内。H2D/forward/D2H/own-stream同期/Rust検査込みのsteady応答中央値:

| batch | CPU ORT | CUDA AOTI Graph | TensorRT Graph |
| --- | ---: | ---: | ---: |
| 1 | 3.6964 ms | 0.7236 ms | 1.0630 ms |
| 8 | 28.4089 ms | 1.6334 ms | 1.0737 ms |
| 24 | 87.3593 ms | 3.5248 ms | 2.7363 ms |

CPUの元ONNXはbatch1固定で、multi-row要求は常駐session内の逐次評価。GPUは真のbatch処理。初回captureと初期化はsteadyから分けて記録する。固定backend順・CPU compilation競合を含む有限検証であり、上表を生成倍率へ読み替えない。

環境はLinux x86_64、Rust 1.98.1、PyTorch 2.14.0+cu130、native ORT 1.30.0、TensorRT 11.3、RTX3060/driver591.86。ORT C API headerはAPI23/1.23.2の一次sourceとMIT licenseを同梱し、実runtime版と区別する。隔離TensorRT SDKは必要分約1.174GBを保持し、共有依存を変更しない。モデル/engine/buildは管理外cache、実験・検証データとSHA/再構成手順はGitで保持する。

## 修復した統合不具合と限界

- 小CPU cycle r1ではbulk cacheの4B単位書込みが遅延した。1MiB BufWriterへ修正し、途中cache/失敗receiptを保持した。
- r2ではvenv Pythonのsymlinkを`resolve()`してbase Pythonを起動した。絶対pathのままvenvを保持する修正後に接続を確認した。
- GPU cycle r1ではPythonのf32 scalerを展開した正確なJSON decimalを、既定JSON parserがf64で1ULPずらしmanifest検査を拒否した。round-trip parserと実decimalの回帰検査を追加し、非f32・非finiteの拒否条件は維持した。
- データは完成gameごとにstream出力し、露出maskは2passで計算する。全教師行をRAMに保持してからexportする設計を避ける。testの分離はAPI/手順であり、OS閲覧禁止を意味しない。
- 上記cycleのαβ行は初版の説明用identity `alpha-beta-static` を保持する。重みmanifest/設定/freezeは別途保存済みだが、この文字列をmodel SHAとは扱わない。統合時に、今後の各行はロード済みNNUE/量子化評価器の内容fingerprint又は距離評価器の型/係数SHAへ束縛する修正と独立identity検査を追加した。旧データは書き換えない。
- 資源はaffinity/cgroup・実物理core・利用可能RAM/VRAMから判断する。小affinityではホストcore reserveを満たせない縮退があり、admission記録で区別する。設定値は上限免除ではない。
- 誘発したGPU初期化faultは10件/forward0で確認した。capture例外・VRAM不足の回収コードは実装/検査したが、実低VRAM/capture failure注入は未実施。
- float/整数SIMDの局所評価速度、ONNX数値対応、cycle完了は棋力向上を証明しない。NNUE最高棋力/正式Sigma NIの目標は継続課題。

## 製品Wasmと保存

最終Linux releaseビルドとCPU/GPU feature付きrunner/inferenceのClippyが成功した。workspaceは72件成功、PyTorch依存の1件は通常実行ではignoredとして別途実PyTorchを指定して成功確認した。Python契約3件、Ruff lint/format、新Python sourceを含む研究境界の構文検査、Web typecheck/render6件、製品rules/ai別featureの検査も成功した。実行ログとコマンドは保存manifestで対応付ける。

同じNNUE/searchをscalarとsimd128のWasmへビルドし、Node上の3合法prefix評価、完了深度callback取消、破損SHA/不正prefix拒否を実行した。JS oracleとの差はこの固定fixtureで0。ブラウザ全環境・将来製品performanceの保証ではなく、Linux性能評価をWasm制約で代用しない。

最終検証コマンドと選択した生データは `research-data/ai-sigma/rust-migration/verification.json` と同ディレクトリの圧縮archive/manifestを参照する。モデル/compiled SDK/build/tensor cacheはarchiveへ入れず、実データ、設定、曲線、予測、manifest、失敗receipt、ログを保存する。既存の研究schedulerは再開せず、旧holdoutや科学記録を書き換えない。
