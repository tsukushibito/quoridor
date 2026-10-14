# 整理後のControl／Cheap × LMR：有限比較完了

共通signed準備と選択した設定・namespace・採点幾何の整理を一image1cc34b4b／Build1108141fへ統合した。両評価器TT1048576、TT/PVS・rules・fullhistory・入力・operation上限・対局clock/物理配置を共通条件から解決。旧400の設定・RAW・勝敗・失敗・費は別subjectとして保持した。

研究判断は、共通化した準備／設定／幾何の実装を保持し、LMRを研究用opt-in・既定OFFのまま残す。Cheapも研究選択肢として保持するが、一律昇格はしない。費用低下と名目深さ上昇は観測された一方、同時間の強さ優位／非劣性は今回確立していない。製品・実generator既定、model/weights/seals、混合・learner全準備/pipelineと323 USERPAUSEは変更しない。

## 96探索の費用

各wholeは6roots・setup/drop・採点/key保存/cache/再探索込み二passの中央値。

| 評価器／採点     |     OFF秒 |     ON秒 |   ON/OFF |
| ---------------- | --------: | -------: | -------: |
| nnue/control     |  7.488890 | 2.123487 | 0.283552 |
| nnue/cheap       | 10.027708 | 3.262289 | 0.325327 |
| distance/control |  3.165968 | 1.183031 | 0.373671 |
| distance/cheap   |  6.180688 | 2.239717 | 0.362373 |

96calls／48sessions、実76,305,132nodes（上限288M）、94COMPLETE＋固定D Control OFFのcoldD6二回だけ8M/completedD5/UNKNOWN。同条件二反復はdepth/valuebits/action/exactPV/allwork一致。Cheap OFFは当該D6を完成。ONは選択的名目深さで全幅と同仕事の速度比較ではない。Cheapの絶対wholeは各評価器・同LMR設定のControlより大きい。

## 同時間128局

左条件の勝-分-負。保存native family-pair bootstrap95%区間を引用し、再bootstrap0。

| 評価器   | 左対右                 | 勝-分-負 | 保存95%範囲      |
| -------- | ---------------------- | -------: | ---------------- |
| nnue     | Control OFF対ON        |    9-0-7 | [0.375, 0.75]    |
| nnue     | Cheap OFF対ON          |    8-0-8 | [0.3125, 0.6875] |
| nnue     | Control OFF対Cheap OFF |   11-0-5 | [0.4375, 0.9375] |
| nnue     | Control ON対Cheap ON   |   6-0-10 | [0.125, 0.625]   |
| distance | Control OFF対ON        |    7-0-9 | [0.1875, 0.6875] |
| distance | Cheap OFF対ON          |    8-0-8 | [0.5, 0.5]       |
| distance | Control OFF対Cheap OFF |   10-0-6 | [0.375, 0.875]   |
| distance | Control ON対Cheap ON   |    8-0-8 | [0.25, 0.75]     |

128unique／64完成色pair、全goal、UNKNOWN/draw/forfeit0。全区間が0.5を含み、同じ8familyを対照間で共有する。固定D Cheapの[0.5,0.5]は全family二色score0.5に由来し、一般同等性の証明ではない。正式棋力/Elo・128独立標本・4条件の間接総順位へ拡張しない。

## accepted完成snapshotの深さ

100ms authority receipt／5ms reserve／depth64／node safety1M／200plyのaccepted観測だけ。中央値が主指標。

| method               |   n | 中央値 |   平均 | min..max |
| -------------------- | --: | -----: | -----: | -------- |
| nnue/control/OFF     | 790 |      5 | 10.306 | 3..64    |
| nnue/control/ON      | 779 |      6 | 11.072 | 3..64    |
| nnue/cheap/OFF       | 794 |      5 |  9.379 | 3..64    |
| nnue/cheap/ON        | 789 |      6 | 10.227 | 3..64    |
| distance/control/OFF | 885 |      8 | 12.295 | 4..64    |
| distance/control/ON  | 876 |     10 | 12.784 | 4..64    |
| distance/cheap/OFF   | 887 |      8 | 11.874 | 3..64    |
| distance/cheap/ON    | 879 |      9 | 11.474 | 3..64    |

小histogramと全depth分布はresult、arena詳細報告に保存。異なる局面軌跡・手数・終盤比率、深い尾部で平均は変わる。LMR ONは選択的名目深さで、全幅深さの保証ではない。NNUE演算単体費や棋力利益をdepth/nodes/secから逆算しない。

全6679 acceptedで実method/LMR/TT1M・receipt/core/terminal/drainを照合。fallback/engine error/failure/receipt>=deadline/未回収terminal/inflightは0。cancelled stop8件はreserve由来で完成snapshot選択と区別。TT83,886,128B/session、二色167,772,256BはRSSではない。terminalworkのみ加算、selected snapshot/persistent gaugesは内包viewを加えない。物理forward・孤立部位費・全検索時間・continuous RSSはUNKNOWN。

## 保存・費用・境界

数値job非重複outer合計848.439982407s、必要software五job（元失敗含む）outer合計231.679882676s。nested native/guardian/sequenceを加算しない。RootInput serde-defaultの初回saved collector照合失敗、元softwarefixture失敗・sourceproof/helper拒否・returned/disk masks・費を保持。source/LLM/admin/保存解析の全費はUNKNOWNで各記録に分ける。

元96calls／128局を一度ずつ回収し、追加root/cap/warmup/sampling/tuning/refill/ゲーム/生成/fitは0。重要な有限解釈だけ同関連reviewerで確認する。

設定・原結果・source/修復・software/関連レビュー・元FAILED/STOPと全深さ分布は[保存receipt](receipt.json)およびexact archiveに保持する。旧400は独立した当時の結果で、今回と混ぜない。関連する有限解釈もblockers0/ordinary0で確認した。追加科学call/gameは0、全USERPAUSEを維持する。
