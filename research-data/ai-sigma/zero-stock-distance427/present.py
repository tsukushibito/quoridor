"""Summarize the frozen427 result only; no RAW or BFS re-entry."""

from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
raw = (HERE / "result.json").read_bytes()
source_ref = dict(
    path=str(HERE / "result.json"),
    sha256=hashlib.sha256(raw).hexdigest(),
    bytes=len(raw),
    mode="0644",
)
result = json.loads(raw)
rows = result["rows"]
assert (
    len(rows) == 161 and result["BFS"]["traversals"] == result["BFS"]["completed"] == 56
)
assert len(result["boundary_checks"]) == 4 and len(result["reverse_checks"]) == 4
summary = {}
for dataset in ("nine", "small"):
    subset = [r for r in rows if r["dataset"] == dataset]
    classes = Counter(r["classification"] for r in subset)
    assert sum(classes.values()) == len(subset)
    margins = {}
    for category in classes:
        selected = [r for r in subset if r["classification"] == category]
        margins[category] = dict(
            T_minus_L=dict(sorted(Counter(r["T_minus_L"] for r in selected).items())),
            rho_minus_L=dict(
                sorted(
                    Counter(
                        r["rho_minus_L"] for r in selected if r["rho"] is not None
                    ).items()
                )
            ),
            saved_labels=dict(Counter(r["saved_label"] for r in selected)),
        )
    summary[dataset] = dict(
        total=len(subset),
        classes=dict(classes),
        finite_Lfail=sum(r["rho"] is not None and r["L"] < r["T"] for r in subset),
        L_passes=sum(r["L_passes"] for r in subset),
        M_passes=sum(r["M_passes"] for r in subset),
        L_greater_M=sum(r["L"] > r["M"] for r in subset),
        margins=margins,
        canonical_E_unknown=sum(
            r["history"]["canonical_history_qualification"].startswith("UNKNOWN")
            for r in subset
        ),
    )
assert summary["nine"]["classes"] == {
    "DISCONNECTED": 1,
    "THRESHOLD_STILL_FAILS": 12,
    "LOWER_BOUND_PASSES": 20,
}
assert summary["small"]["classes"] == {
    "THRESHOLD_STILL_FAILS": 126,
    "BOUND_TOO_WEAK": 2,
}
assert all(
    not (r["rho"] is not None and (r["M"] > r["rho"] or r["L"] > r["rho"]))
    for r in rows
)
BFS_purposes = Counter(x["purpose"].split(":", 1)[0] for x in result["BFS"]["ledger"])
assert sum(BFS_purposes.values()) == 56
presentation = dict(
    result=source_ref,
    datasets=summary,
    groups=result["groups"],
    representatives=result["representatives"],
    BFS=dict(
        traversals=56,
        purposes=dict(BFS_purposes),
        visited_vertices=result["BFS"]["visited_vertices"],
        scanned_directed_edges=result["BFS"]["scanned_directed_edges"],
    ),
    checks=dict(
        selected161=True,
        exclusive_classes_sum=True,
        max_each128=True,
        no_finite_bound_contradiction=True,
        boundary_definitions=4,
        reverse_pairs=4,
        RAW_stream_reads=1,
        RAW_other_rows_parsed=0,
    ),
    no_recompute="read saved result only; zero BFS/RAW/solver/Search/model calls in presentation",
)
(HERE / "presentation.json").write_text(
    json.dumps(presentation, ensure_ascii=False, indent=2) + "\n"
)
report = """# 427：零在庫の距離下界と十分条件の限定切り分け

この固定保存標本では、有限な距離下界Lの不成立に対して、**真の壁距離rhoを使っても同じ閾値を満たさない状態の方が多かった**。9×9の有限L不成立12件すべて、補助のL不成立W/L128件中126件がrho<Tだった。9×9の別成分1件をこの二分類へ押し込んでいない。この結果だけで一般原因、Search内部の分布、勝敗、速度、棋力を認定しない。424候補や比較専用経路は復活させない。

## 対象と固定順

9×9は元411の8exact prefixのうち双方stock0・非終端の5rootを先に置き、その出所の旧408 batch000ゲーム0〜3を保存順で採った。各ゲームで最初の双方stock0から最大32個の異なる盤面+壁+手番という事前規則だったが、実在した非終端状態はそれぞれ11/1/9/11件。root4〜7と各ゲーム先頭の4重複を同一rowへ統合し、両originは保持した。元root3を含め33個の異なる状態、5壁集合となった。上限128との差95はこの固定保存範囲での実在数不足であり、紛失や追加ゲームによる補充ではない。元root0〜2は在庫6/4/2のため対象外と記録した。

読んだ原streamは指定のcompleted.jsonl.gz一本だけ。物理read1回、最初4行のみJSON解析し、残り28行はCRC/raw hashのためにdrainした。compressed SHA1f459b5f/1052734B、raw SHAb773bd1e/5609998Bは旧boundと一致。読取前後のinode/size/mtimeおよび同buffer hashは一致し、diskを二度hash読取したとは主張しない。元RAWや全movesを出力へ複製していない。

補助は414が用いた52fixtureの安定順（fixture ID→raw ID）で、保存active W/LかつL<Tの先頭128件に固定した。174 W/Lをフィルタすると最初の3fixtureだけで128件となり、全て3×3（mask0/1/2）、保存W76/L52。5×5まで到達しなかった。辺・rank payloadはskipのみ、旧WDL/oracle/52suite/39708Drawや全配置を再実行していない。9×9の選択は幾何判定前、小盤面のL不成立フィルタもrho計算前にselected-states.jsonへ固定した。結果を見た入替えは0。

## 分類

rhoは占有・jumpを無視した普通の壁辺グラフのa-b BFS距離。P0のgoalは最終row、P1はrow0、ds/doは実手番から選び、ds<=doならT=2ds、そうでなければT=2do+1とした。各goal差は両端有限の場合だけ採り、sentinel n*nや欠落を差へ入れない。正しい同壁・同寸法の2goal表を必要な壁集合だけ一時再用した。

| 集合 | 状態 | L>=T対照 | L<T<=rho：下界取り逃し | 有限rho<T：同閾値で救えない | 別成分 | 盤面幾何前提不適合 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 9×9固定保存 | 33 | 20 | 0 | 12 | 1 | 0 |
| 補助・先頭L不成立W/L | 128 | 0 | 2 | 126 | 0 | 0 |

各行は排他的分類の和。幾何前提の0は壁配置・在庫・盤面終端・自goal有限の確認範囲だけで、全prefixの新たなnative合法性認証ではない。別成分はrho=null/infiniteとして独立にした。M通過数とL>M数、T-L/rho-Lの実分布、dataset/game/root/壁集合別表はpresentation.json。複数originのgroupは同じrowを共有するためgroupを合算して独立標本数へしない。

9×9の12有限失敗は全件L=rhoで、T-Lは1/3/5/7/9だった。小盤面の取り逃し2件はいずれも保存Wで、T-L=rho-L=1。残る126件の保存ラベルはW74/L52であり、WDLラベル自体は変更していない。

9×9の12有限失敗では、正確なrhoへの置換だけではこの十分条件を救えなかった。これはDrawやLossの証明でも、別の十分条件が不可能という証明でもない。L>=T対照20件も勝敗・実proof leafの実測ではなく幾何通過数である。

## 元順の代表例

cellはrow*n+col、0始まり。全壁ID/mask、origin、ds/do/M/2goal差/L/rho/T、T-L/rho-L、historyの既知/不明はresult.json各rowに保存し、各dataset×区分から最初最大2例をpresentation.jsonへリンクした。

| 対象 | P0/P1/turn | ds/do | M / goal差 / L | rho / T | 区分 |
| --- | --- | --- | --- | --- | --- |
| 9×9元root3 | 60/56/0 | 4/8 | 4 / [1,2] / 4 | 無限 / 8 | 別成分 |
| 9×9root4=game0 prefix54 | 58/47/0 | 6/13 | 3 / [3,3] / 3 | 3 / 12 | 真距離でも不成立 |
| 9×9root6=game2 prefix43 | 32/11/1 | 5/16 | 5 / [5,1] / 5 | 5 / 10 | 真距離でも不成立 |
| 9×9root5=game1 prefix50 | 63/38/0 | 1/6 | 5 / [8,5] / 8 | 9 / 2 | 既存L通過対照 |
| 9×9game0 prefix59 | 51/37/1 | 15/3 | 6 / [8,8] / 8 | 8 / 7 | 既存L通過対照 |
| 3×3fixture1 raw9 | 0/4/1 | 2/4 | 2 / [3,2] / 3 | 4 / 4 | 下界取り逃し（保存W/Lは原rowを保持） |
| 3×3fixture2 raw45 | 2/4/1 | 2/4 | 2 / [3,2] / 3 | 4 / 4 | 下界取り逃し（保存W/Lは原rowを保持） |

## 履歴・検証・費用

9×9の完全saved action prefixから、initialを含む全到着の単位countを保持して現在壁/stock0 domainのEを別途集計した。derived Eemptyは33件ともtrue。しかしこのPython会計をcanonical weighted-base+overlay/HistoryKeyのnative再生資格へ昇格せず、canonical履歴資格および実proof leafはUNKNOWNのまま。小盤面W/Lはhistory-freeの保存ラベルで、実履歴は128件ともUNKNOWN。geometryと実threefold・fullhistory資格は別である。元prefixに対する既存native資格を本解析が新しく再検証したとはしない。

canonical405boardと409distancesのAST関数だけを呼び、別BFSやsolverを複製していない。有限rhoに対するM<=rho、各有限goal差<=rho、L<=rhoは全件一致。意味ある新4境界定義（同閾値失敗、合法単一V壁の取り逃し、等号通過、synthetic別成分/欠落/sentinel81の項別除外）と、各集合先頭2点の逆向きrho確認を実行した。synthetic graphを合法Quoridor反例とは呼ばない。検証込み全BFSは56/1024、全状態161/256。訪問頂点/走査辺とpurpose別ledgerはresult.jsonおよびBFS-ledger.json。矛盾・追加review questionは0。

child内部wall0.02453931697527878秒はsourceguard外側時計にnestedであり加算しない。LLM/全admin費・連続family peak/isolated map費はUNKNOWN。512MiB family（controller込み）、CPU3/G7、GPU0、host reserve4GiB、no_new_privs、fresh topology/affinity/選択physical peer検査を各維持guardへ保存した。affinityだけで公平なtiming/全hostquietを認定しない。原buildSTOPは参照のみ、新native/model/Search/solver/Perf/game/fitは0。

## 判断の限界と次の問い

この狭い集合では、下界強化の不足より同じ安全閾値の厳しさが支配的だった。ただし9×9は2共有familyの4終盤ゲームと別1root、補助は先頭のほぼ無壁3×3に偏る。旧424の約260万回の内部L検査へ頻度を外挿せず、時間短縮率や省ける部分木を推定しない。別成分1例と小盤面の取り逃し2例は残るが、production candidate復活・rho用追加BFS/cache・新閾値を今回の標本だけから採用する根拠にはしない。

次に必要なら、実際の内部失敗nodeが同じ型かを、別途事前固定された限定観測で問う余地がある。これは提案だけであり、新observer/実装/計算/対局/追加rootを開始していない。426のNNUE検証は独立で本解析完了をgateにしない。全旧RAW/FAILED/費UNKNOWN、342.17/323等USERPAUSE、models/weights/seals/oldfits96、製品/generator既定・foreign変更を保持する。本人leafの状態/受入れはBeads、実STOP/refs/usageはcompletion packetへ一度まとめる。
"""
(HERE / "report-ja.md").write_text(report)
assert (
    hashlib.sha256((HERE / "result.json").read_bytes()).hexdigest()
    == source_ref["sha256"]
)
print(json.dumps(dict(summary=summary, BFS=56), ensure_ascii=False))
