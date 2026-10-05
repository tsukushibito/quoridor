# PVパイプラインの保存教師入口 / quoridor-4lc.160

契約cd4aa344、枠10、受領03:06:45UTC。本人claim/start配送済み。主配分158/159と独立したNN0静的準備。151 StageA-r2のreference固定5根だけをJSONLへ抽出し、再読込validatorとgroup split smokeを実装した。5行/5group、train4/validation1。これは診断fixtureであり学習ready・正式holdout・汎化・棋力ではない。

features648のf32bitsは保存fixtureと一致。合法historyのkey/count集合、side/ply/prefix、root keyと残壁を保持。history配列順は原fixtureとrootで異なる場合があるため集合を照合し正規順へ統一、prefix順は保持する。全根K32/rootN32/edge visits和31、π136は訪問分布でNNpriorとは別。Rust209の実着地からSigma136へ対応し、P2の上下反転・壁anchor反転を検査。rootNN/rootmeanとP1符号変換は別field。game zと深部leafNNは欠測、StageA検索結果から終局を捏造しない。原RuleA合法根の保存根拠を使用し、独立合法replayは今回していない。

同一fullstate（残壁/history/side/plyを含む）＋prefixをSHA group化、engine/ラベルをgroupから除く。重複candidate/referenceを異splitへ置くmockは拒否。shape/NaN/不正mass/負visits/P2対応/符号を含む7拒否mockとP2 jump/H/V/involution確認が通る。export-2の合法手dict schema例外、export-4のhistory順一致例外を保存し同scope修復した。科学教師のNN再実行0、失敗を旧成功へ付替え0。ゼロvisitは学習policyとして拒否しuniform/priorへ置換しない。terminalは本5根にない。将来は真の保存終局と視点がある時のみzを付け、訪問無しterminalをπ教師へ変換しない。

source/run/model/rules/encoder/fixture/clock/Kの保存SHA-byteはprovenance.jsonと各行sourceにbind。根NNとrootmeanは手番視点で、leafNNの平均やgame結果ではない。固定Kは同wall/同CPUではない。初期/asym/jumpという既人工golden3根を含み選定偏りを持つ。正式holdoutは158159校正入力やこの5根と分離する。

PyTorch2.14.0+cu130等はinstalled dist-infoの静的確認だけ。torch import/CUDA動作/学習は実行0。scripts/dev/training.shは環境launcherでありselfplay/trainerではない。限定確認したtools/trainingには環境検査しかなく、既モデルはONNX。元PyTorch構造/state_dictと重み移送が足りず、継続学習を用意済みとは言わない。全保存sourceの不存在監査はしていない。

次案は1つ：小さい初期重みPVモデルのCPU toy pipeline smokeを別配分する。担当experiment、private tools/ai-sigma-pv-toy-pipeline/・専用data、共有環境編集0。固定8新legal-prefix群から自己対局4pair/8gameを既Sigma教師で生成しπ/z/rootmean/教師予算を保存、結果前group train6/validation2を固定。Σモデル継続ではなく新PyTorch小構造の初期重み開始を明示。CPU loss/backward/checkpoint→同一checkpoint再読込/ONNX出力parity→version固定→既同wall arena最大4pair/8gameを一つの有限パイプラインとして検査する。生成は結果による追加/置換0。教師生成とarenaは各200ply×500msなら各800秒の対局時計上限、init/停止/保存は別、CPU1/ブラウザRAM6GiB guard5.5、toy train CPU1/RAM1GiB/120秒、writer45分・独立確認10分を見積る。保持教師8MiB・checkpoint/export4MiB・log4MiB、移管重複/Git別を新配分で確認。未測定の見積りを許可にしない。現在GPU学習追加0のため本枠はデータ入口と計画まで。本学習は少なくとも新分布教師数・CPU/GPU実費・保持・停止を改めて見積り、toy損失低下を本学習費用推定にしない。

split/parity/復元失敗なら収集schema又は構造を修復し棋力arenaへ進まない。CPU smoke成立なら実費を基に教師生成と本PV学習を選定する。arena悪化/不明なら教師・探索・量を分けて採用保留、改善方向でも8局でSigma同等を認定しない。NNUEは後続候補で、PV全完成を恒久gateにしない。学習loss/teacherfit/速度は棋力でなく、固定モデルの独立同資源比較を段階目標とする。

全コマンドはCPU0、NN/Chrome/model-load/build/game/GPU/training/download/delegation0。管理commandログに開始終了/版/必要結果/子identity/waitを保存。過去peakと現在RSSを分ける。現在identity不在は自然終了・全期間/全host保証ではない。受入れはcoordinator、goal/他者close0。
