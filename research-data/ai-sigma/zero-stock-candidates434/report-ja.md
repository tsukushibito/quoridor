# 壁ゼロ確定条件5項目の有限比較434

固定主32rootのobserver OFF Search合計では、D（同一winning witnessのfuture-Q履歴資格）だけが両評価器の事前条件を満たした。差はNNUE約0.71%、fixed D約0.18%と小さく、局所悪化がある。Dは明示的な研究optionとして保持する。通常研究の既定はP（enable=true / path_tail）のままで、製品・generator・MCTS、全量教師の固定safe OFFには継承しない。

## 固定した比較と結果

元433の真正な二系列・32rootを完全prefix/historyで用い、系列・色別の四persistent sessionsを維持した。BEST43 NNUEとfixed D、Control/PVS/TT1M/LMR ON depth_rank/旧approx OFF、nominal D8・各4M nodes・時間上限なしである。A–DはPへの単独追加、EはMに対する旧424 global Lで、候補の混合・結果を見た再選択はない。

各項目・評価器のOFFは対照→候補→候補→対照、ONは各一回。全60 operations・1,920 callsがCOMPLETE/DepthComplete、UNKNOWN0、実29,411,193 nodesで、7,680,000,000 nodes上限内だった。主時計は各pass32 callsの最終Search秒和、表は二OFF反復の中央値（二値の算術平均）である。

| 項目 | 単独の追加条件                              | NNUE 候補/対照 | fixed D 候補/対照 | 両評価器の事前条件 |
| ---- | ------------------------------------------- | -------------: | ----------------: | ------------------ |
| A    | 最初のP経路失敗後だけ有界shortest DAG       |       0.939108 |          1.006110 | 不成立             |
| B    | 同じ最初の経路の地点距離下界                |       0.975295 |          1.127454 | 不成立             |
| C    | qualified cross-unreachableの別成分race     |       1.020954 |          0.905240 | 不成立             |
| D    | 同じ受理witnessのfuture Qとweighted二回集合 |       0.992947 |          0.998187 | 成立               |
| E    | M失敗後の旧global L                         |       0.974400 |          1.037698 | 不成立             |

A/B/EはNNUE側、Cはfixed D側だけで成立した。B/fixed Dではseries1の双方候補反復も対照中央値の1.10倍を超えた。root単位の同じ警告数はA=2/2、B=3/3、C=2/0、D=1/2、E=2/0（NNUE/fixed D）。警告は局所悪化の記述で、新たな採否閾値ではない。

同methodのOFF二反復20組とON/OFF20組は、各32行の保存projectionで値bits/action/PV/status/depth/旧work/fullhistory/TT generation/親復元が一致した。全640 ON行でnode分割・span閉鎖・復元も一致した。候補間には異なるproofと選択木による値・PV・work差を許し、同一workの速度や未訪問nodesの節約へ換算しない。

## 発動と限界

Aの専用DAG fresh returnsは16/40、Bのpoint条件を必要としたfresh returnsは1,818/2,211、Cの別成分fresh returnsは2/5、Eのglobal L fresh returnsは2,496/3,739だった。地点pass・geometry pass・fresh committed return・typed TT returnは異なる分母である。Aのpath_passesはDAGも含む。

Dはfuture scans/returnsが30,467/35,244、history itemsが1,413,685/1,641,354、future history rejectsは0だった。これには従来M/Pでも成立する例を同じQで検査した戻りが含まれる。同一訪問状態でglobal Eが非空かつQだけを通した件数は保存counterに無く、追加資格の実件数はUNKNOWN。seen 206×u64=1,648Bの一時bitset初期化、Q/witness形成、weighted history走査、controlは実費で、分離時計・最適化後stack・continuous peakは未測定である。

ONのpositive-root最大stock0 spansと、stock0開始root全Searchは非重複に扱った。ON−OFF差は正負ともあり、正確なoverhead補正にはしない。native RUN wallは全60個合計52.401206458秒、Search和27.350908724秒はその内包時計である。outer584.896926748秒を一度数え、nested時計を加算しない。副時計の固定残差配賦は全60 passで非負・完全だったが、配賦額をroot単独の因果費用とはしない。

optional入力は結果前にUNSELECTED_MISSING_QUALIFICATION、selected/calls0と固定した。有限poolの必要なqualified map/witness/historyが不足しており、機会はUNKNOWNである。「機会なし」や結果後の勝つroot探し、未使用枠のrefillにはしない。相関した二系列・二反復・固定評価器の結果から一般速度、棋力、母集団有意差は主張しない。

## 保持と証拠

Dを明示研究optionとして残し、完了比較専用のA/B/C/Eおよび用途を終えた434観測API/counter/fixtureを整理対象とする。P/M/Dの現役の正しさ、完全weighted history、typed TT、true terminal/root/control/undoは維持する。通常研究Pの既定、明示OFF/M、全量教師のsafe OFF、USERPAUSE、封印、モデルは変更しない。整理後sourceのsoftware検証は元実測とは別証拠であり、元imageと同じ速度を測定済みとはしない。

この保持方針の整理sourceを、Mainの実16対象のbefore SHA/bytes/modeと照合して採用した。8変更・8削除で、A/B/C/Eのmethod/ID・専用moduleと比較fixture、434 timer/flag/専用API/counter/serializerを撤去し、互換alias・常時0 fieldは残していない。Dの成功は既存の汎用path return counterへ記録する。D helper・既存D4定義・連続sessionのcorrectness fixtureは全bytes一致で保持し、P/Dは同じ一回の経路walkと成功時だけのwitness記録を使う。LCの変更は既存2関数のみである。

必要なplain AI tests compile、撤去名拒否とM/P/D名・IDを確認する新しい純粋metadata定義1件、AI/runnerのaffected Clippy（tests＋diagnostics/measurement、-D warnings）が実PASSした。新1件以外の旧成功assertion・D4・連続session suite・model/head/Search/performance/releaseは再実行していない。Rustfmt、LC lintと変更2関数のproject Ruff整形チェックも通過した。Rootの整形用抜粋が関数間の空行を一つ欠いた失敗は保存し、抜粋生成だけを修正した。採用source自体の変更や旧検査の再演にはしていない。[厳密採用・必要software・全失敗domain・STOPの受入れ証拠](../../../.artifacts/research-team/integration324/zero-stock-candidates434-v1/retention-adoption-v1/completion.json)。整理後sourceの速度・棋力はUNMEASUREDのままである。

元測定はsource commit `2b4f22e68801854985e4a7702978eda9dc88227c`、accepted BUILD `0527f2d31e569604471f55f429eea09d16b1af16cb8dbcac82e2fecb0410340f`、image `defbadf91c086d01c47b7d3e318eea3ca83e756a5d342e08973c70022c4edcc0`、原job `fba39669-0994-4915-9cce-d4bffa7bca8d`へ束縛する。元RAW/manifests/capture/FAILEDとmetadata回復・NULL-vs-diskの区別を保持し、archive/restore/削除は行っていない。

- [実collector・1,920 calls・STOP](../../../.worktree/assets/perf/zero-stock-candidates434-implementation-v1/A/recipe-settings-v1/collection-v1/completion.json) — SHA256 `5d9e8ba5fbc8e414f1b71abfdc6b9c077c92377f8d5b48de3ad8c503fd04db8b`。
- [元の詳細保存解析](../../../.worktree/assets/perf/zero-stock-candidates434-logic-analysis-v1/results-v1/report-ja.md) — SHA256 `71bc1914c985a3ecd0f1c6bfbe6be776e90db3e66b6c2e733af3c5d7d237e530`。図、全root/series/counter/時計CSVと保存算術sourceは同results-v1にある。
- [解析の完全FileRef binding](../../../.worktree/assets/perf/zero-stock-candidates434-logic-analysis-v1/results-v1/final-binding.json) — SHA256 `06ba7662194bd20aceb3f191f16511cf21600e9b0b1be94bfa4e897920e3354c`。
- [Rootの保持判断](../../../.artifacts/research-team/integration324/zero-stock-candidates434-v1/retention-direction-v1/decision.json) — SHA256 `06480865fc7959350af4167740d766545f52350b70334f653d91a77faebdecde`。

保存支持は576MiB=603,979,776Bの一回のunionで、旧200MiB案は未適用のまま。used/FAILEDの返金・旧holding再課金はない。global actual、全費用、continuous peak、物理NNUE回数はUNKNOWNを保持する。
