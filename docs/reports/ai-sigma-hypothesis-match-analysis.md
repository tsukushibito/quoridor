# SIGMA-MATCH-HYPOTHESES / 試行1 / 版1
quoridor-4lc.27、hypothesis → coordinator。目標版2/04:00UTC継承。固定32局の探索的分析完了、goal未達・正式NI未立証・採用0。

1534要求を固定revision3審判で合法prefixから再生。native371/Wasm395/参照768。native対参照371×370中、盤面/手番一致55→全履歴/残ply/prefix一致48組。Wasm対参照395×398中67→56組。native対Wasm371×395中120→97組。差7/11/23は履歴不一致、残ply差0。各48/56/97ユニーク根/各側要求、初手各8組。seed1979/T500/g91と要求limits欄一致、実t0一致0（交互要求）、時計誤差/負荷は別。参照実cap100000、候補4096/node512/depth24で探索規則も異なる。backend単要因介入0、97組も経路一致後の観測で独立標本ではない。

同根NN回数中央値はnative/参照60/22、Wasm/参照8/22、native/Wasm61/9。後者の要求内NN中央値の中央値4.271/47.600ms、着手一致83/97。子孫NN入力まで対応せず、速度→勝敗の因果未確定。

競合説明と反証案（未実行、詳細JSONに根拠/予測/gate/費用）:
- H1 backend/host費用。全20合法goldenで評価器だけtract/ORT交換、1NN・8/32sim・同時計比較（15分）。数値abs1e-4+rtol1e-4、finite/value[-1,1]/fallback0/取消拒否を先にgate。速度・有効展開増なしなら弱まる。.26独立resume gate依存。
- H2 探索規則。候補C1.5/Q0/sqrt(N+1)/prior→seed tie、参照C1/FPU.2/sqrt(N)/先頭tie。固定oracleのpath/rootを一要因ずつ比較（5分＋必要NN15分）、同workで不変なら対象例で反証。765候補根edge訪問和sim−1、参照768根visits sim+1。候補最大訪問tie18/371・110/394、参照rootedges/PVなし。
- H3 NN/IPC/checkpoint/terminal。native4096sim到達9、nodecap true0、54/371要求sim>NN、Wasm13/394も同様。固定局面でNN/checkpoint/配送を一箇所ずつ遅延注入（10分）、全区間T内でも拒否なら会計/時計説を再検討。終端再訪の安いsim、旧g25negative、late救済0を保持。
- H4 小標本/色/局面。native先5W3L/後4W4L、browser先2W6L/後1W7L、各n8。新pool/m/NI規則は別契約で勝敗前固定。T.5/200plyで最大100秒/局、両platform各mなら400m秒。m48は19200秒で残3時間超。既成績へCI/m後付け0。

native9W7L/.5625、browser3W13L/.1875維持。game3応答なし527.096867ms、game5合法手32late拒否502.309811msは候補loss。欠測1を0補完せずNN時間分母23816/15924/3337、Wasm要求分母394。同モデル28件の数値互換性は既受入れ、A共通Rust/B分離ORT/C B0保持。

詳細/再現: .artifacts/ai-sigma/analysis/SIGMA-MATCH-HYPOTHESES/ のJSON/script/process/log/hash。CPU0/各45秒内読取、76受入れ入力を含む138hash前後不変。HEAD/lock/threadはledger。schema誤読を再抽出し失敗版保持。

00:47:41停止JSON/PID0を報告生成前保存。監視childCPU9.594秒/RSS201306112B、新規約6.6MB/32MiB内。補助読取RSS/TID未採取・50ms欠測で全面証明なし。NN/build/取得/対局/学習/GPU/委譲/他者kill/削除0。旧逸脱・tail/来歴/合法200/no-legal/深部/entropy/license未確認保持。.18限定受入れで本人close。報告保存後書込終了・temp残存なし。.27受入れ待ち、次は統括別契約。
