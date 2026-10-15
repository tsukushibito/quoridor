# 壁迂回を使う安全先着条件の拡張計画（414）

計画と根拠の確認を完了した。候補は `L=max(M, finite |D0[a]-D0[b]|, finite |D1[a]-D1[b]|)` の一つだけ。正確な同壁・同寸法・同goal方向の表なら各有限距離差は普通の壁辺で1-Lipschitz、壁グラフの二駒間距離の下界となる。Mとのmaxも下界で、411の安全先着証明へ代入できる、という条件付き定理を独立max担当が確認した。

勝者の普通最短路長n、相手先行ならδ=1/勝者先行なら0について、L>=2n+δなら相手起点から路上の全頂点まで少なくともL-n>=n+δ。相手が使えるn-1+δ手では最初の路上占有・jumpに必要な隣接も間に合わない。相手goal距離もこの手数を超えるので先着する。従ってds<=doかつL>=2dsなら手番側W、do<dsかつL>=2do+1なら相手W、それ以外UNKNOWN。等号・tie・最後の隣接/goal占有・sidejump・非連結を含む限定前提は[独立論証](review/report-ja.md)に記載した。到達不能81（小盤では各盤のsentinel）を差から項別に除き、もう一方の有限項とMを保持する。

盤面先着と実履歴のthreefoldは別の条件である。完全なcanonical weighted base+overlay集約で現在の壁/stock0 domainのcount>=2集合Eが空であること、true goal/threefold優先、root通常比較/positive childdepth/depth0維持、fullhistory/TT種別・depth/domain/undo/controlを411どおり必要とする。from_countsの形やis_synthetic=falseを真正chronologyとみなすshortcut、履歴資格の削除はしない。

| 保存集合           |  件数 | 旧W/L/UNKNOWN | 新W/L/UNKNOWN | 追加W/L | false-Proven/未検査 |
| ------------------ | ----: | ------------- | ------------- | ------- | ------------------- |
| 52保存fixtureのW/L |  5680 | 1393/476/3811 | 1469/512/3699 | 76/36   | 0/0                 |
| 409保存Draw flags  | 39708 | 0/0/39708     | 0/0/39708     | 0/0     | 0/0                 |

全45388件で旧条件の包含を保存確認した。追加112件は3×3で40W/16L、固定5×5で36W/20L。13新境界定義を一度確認し、独立担当は134層の保存算術を確認した。元52のWDL/辺/rank solverや全2.5M配置を再実行していない。有限の誤確定0は一般証明の代わりではなく、9×9の成立頻度や実履歴資格・速度を示さない。[保存結果](saved-check/report.md)。

実装可能性は既存411 WallDistanceScratch/正確なFloat map所有に基づくsource調査だけで、production patchは0。既存TT hitと旧M成功は追加参照0、旧Mが幾何UNKNOWNで既存の同wall pairがあれば交差u8セル2点・各有限guard・最大2 abs_diff/2 maxで強化できる。pairが確認できなければ旧M/UNKNOWNを保持し、新しいmap/BFS/81セル走査/clone/heap/cache/APIは足さない。既存map取得は無料でも新414費でもなく共通wholeに含む。追加の幾何成功は完全E scanやTT leaf処理、探索の訪問数も変え得るため「全費用が2参照」とは言わない。実borrow/typing/layout・動的頻度/時間・速度利益はUNKNOWN。[source費用調査](source-cost/report-ja.md)。

後続案は同一の将来imageでOFF/旧M/新LをO→M→L→L→M→Oと比較する。NNUE BEST43/固定D(0,8,tanh)×別々のLMR OFF/ON-depth_rank、元411の8真正prefix、各root cold→同session warm、Control/PVS/TT1048576、旧近似OFF、D8/各4M nodes/時間上限なし。384 calls/192sessions/1.536B nodes上限。setup/reset/履歴/距離/Search/drop込みwhole、各root/温度/反復、通常評価/NNUE delta、stock0機会、fresh旧M失敗→L成功、history拒否/実proofleaf/TT再用を分ける。TT由来で証明元が不明なら再計算してtelemetryを捏造しない。内包時計・gaugeを加算せず、未完成・異value/PV/仕事量は同仕事speedupやroot exact WDLにしない。重い残壁6/4にも効くかは未測定で、結果を見たroot/上限/係数変更・補充・新対局を足さない。

[具体的な将来計画](future-measurement-plan.json)のimage/Build/runtime/admissionはnull/未入場のまま。今回の完了は論理・保存照合・費用形と有限計画の具体化であり、実装・software・384callsの実行完了や開始許可ではない。旧411/412/413/415のimage/source/RAW/結果を再演・置換しない。

新保存predicate runの外側1.920527222秒とchild1.764705522秒はnestedで足さず、旧WDL/対局/探索費を加算しない。全source/LLM/admin費・連続RSS・physical NN・孤立predicate時間はUNKNOWN。元lint/表記/source helper失敗・returned対disk masks・STOPを[receipt](receipt.json)とexact saved-plan archiveへ保持した。全mixed/learner prep/pipeline・323 USERPAUSE、製品/generator enable OFF、models/weights/seals/oldfits96/foreign変更を維持し、Root/human ACKを今回の計画工程のgateにしていない。
