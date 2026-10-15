# 固定1手対深さ・順位LMRの有限結果と判断

同一image bb63fc17/Build e934c534/native source0abbb。A=fixed_one、B=depth_rank。NNUE BEST43と固定D(0,8tanh)、Control/Cheapで別stratum、TT1048576/PVS、零在庫近似OFF。source/必要softwareとは別に今回の有限観測を判断する。

## 探索費

96calls/48sessions/288M cap、実31,210,438nodes、96COMPLETE/0UNKNOWN。6rootsとcold/warm寿命を再用し各stratumでA→B→B→A。二反復のdepth/valuebits/action/PV/保存work一致。

| 評価器/採点      | A whole中央値s | B whole中央値s |      B/A | valuebits/action/PV差root数 |
| ---------------- | -------------: | -------------: | -------: | --------------------------: |
| nnue/control     |       2.188403 |       1.918021 | 0.876448 |                       4/1/4 |
| nnue/cheap       |       3.292407 |       2.601276 | 0.790083 |                       6/5/6 |
| distance/control |       1.305124 |       1.109529 | 0.850133 |                       0/1/2 |
| distance/cheap   |       2.250010 |       1.875141 | 0.833392 |                       2/2/2 |

wholeはsetup/drop・表初期化・採点・TT・再探索を含む。全4条件でBが短いが、異なる選択探索の仕事であって同仕事speedupではない。全名目D6も全幅保証ではない。Cheap/Controlの絶対whole・nodes/evaluations/delta/LMR/TT/PVSと局面別時間はcost96-presentation-v1/result.jsonへ保持する。TT retained/generationはgaugeなのでイベント合計へ加えない。

## 同時間128局

同じ16families×2色×4対照、128unique/64complete pairs、127goal＋1threefold draw、UNKNOWN0。100ms authority receipt/5msreserve/1M safety/depth64/200ply、AI2/6/main4。表はA側、区間は元native family-pair bootstrapの保存値（新bootstrap0）。

| 評価器/採点      | A勝-分-負 |  A score | 保存95%区間          |
| ---------------- | --------: | -------: | -------------------- |
| nnue/control     |   13-0-19 | 0.406250 | [0.28125, 0.53125]   |
| nnue/cheap       |   12-1-19 | 0.390625 | [0.234375, 0.546875] |
| distance/control |   12-0-20 | 0.375000 | [0.25, 0.46875]      |
| distance/cheap   |   12-0-20 | 0.375000 | [0.25, 0.5]          |

B側scoreは0.59375/0.609375/0.625/0.625。固定D Controlの保存区間はB優勢側にあるが、共有16families・4対照・固定book条件付きであり、多重対照/系譜依存を補正した一般優越ではない。その他は0.5を含むか接する。128独立標本/Elo/非劣性は主張せず、追加対局/追試/tuningを自動発行しない。Control対Cheapの直接対局は今回なく、対照間scoreからその順位を作らない。

## accepted完成snapshot深さ

| method                      |   n | 中央値 |      平均 | 1..3/4..5/6..8/9..15/16..31/32..63/64 |
| --------------------------- | --: | -----: | --------: | ------------------------------------- |
| nnue:control:fixed_one      | 769 |      6 |  9.729519 | 8/371/62/154/167/5/2                  |
| nnue:control:depth_rank     | 772 |      5 |  9.869171 | 15/381/48/150/166/6/6                 |
| nnue:cheap:fixed_one        | 763 |      5 |  9.036697 | 111/312/83/121/118/5/13               |
| nnue:cheap:depth_rank       | 767 |      5 |  8.795306 | 126/293/87/125/122/4/10               |
| distance:control:fixed_one  | 864 |     10 | 12.466435 | 0/312/98/209/210/17/18                |
| distance:control:depth_rank | 868 |     10 | 12.796083 | 0/311/85/223/201/21/27                |
| distance:cheap:fixed_one    | 880 |      9 | 11.589773 | 27/339/61/168/264/4/17                |
| distance:cheap:depth_rank   | 884 |      9 | 11.995475 | 29/310/86/185/243/6/25                |

全6567 acceptedのみ。双方LMR ONで選択的nominal depth、A/Bは異軌跡・手数・終盤比を持ち、平均は深い尾部に影響される。NNUE ControlのB中央値5はA6より低いが、全幅深さ/勝因/一般強さへ換算しない。最後20記録plyは時系列proxyで終盤属性そのものではない。

fallback/engineerror/forfeit/receipt late-or-equal0、全acceptedでterminal matching/inflight0。receiptは期限前だがterminal return後408/commit後441は別scopeで、deadline超過receiptと混同しない。reserve stopはusercancelではない。terminal workとselectedsnapshot/永続TT profileは内包viewを重複加算しない。実TT83,886,128B/色はRSSでなく、物理NNforward・孤立費・continuous family peak・全process Search CPUはUNKNOWN。

## 研究経路の判断

depth_rankを研究用opt-inとして保持する。固定1手も既存の明示方式と省略時methodとして保持し、製品/実generatorのLMR既定OFFは変更しない。今回の有限費用と対照scoreは継続使用を支持するが、一般棋力優越/非劣性/最適係数/正式昇格は認定しない。Cheapの新しい一律昇格もしない。履歴補正・適応再探索・追加candidate/parameter sweepは発行しない。同408.3の限定最終解釈でもblockers0/ordinary0を確認した。

非重複software outer（原FAILED含む）145.596757941s、数値outer（原pre-game拒否含む）799.283536230s。nested native/guardian/sequenceは加算せず、source/LLM/helper/admin/saved解析を含む全費はUNKNOWN。

原arena128-v1はforecast49,057,749B>32MiBで入場前拒否し、原FAILEDと費を保持。出力上限64MiB＋freshpathsだけへ通常修復し、真正未入場128を一度実施した。原96/128を再演/補充せず、旧400/402/406/407/409と混ぜない。全pause/defaults/models/weights/seals/oldfits96/foreign/旧RAWFAILED費UNKNOWNを維持。

設定snapshot・原結果・source/software/失敗/STOP・全深さ分布と独立確認は[保存receipt](receipt.json)とexact archiveに保持する。科学用imageは凍結版のままであり、この文書commitに合わせた再buildは行わない。
