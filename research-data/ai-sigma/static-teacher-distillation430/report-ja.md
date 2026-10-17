同じBEST43・NNUE・入力・実更新列で、終局z（Z）、固定Sigma単体値（S）、固定Claustrophobia1.3.1単体値（C）を比較した。各LAST118を使った有限対局では、主要C対Zは67勝61敗、52.34375%、95%区間[46.09375%,58.59375%]で、事前の下限>50%基準は未達だった。副次S対Zは63勝65敗、49.21875%、[42.1875%,56.25%]の記述的結果である。両対照は同じ64開始familyを共有し、各両色128局、計256局すべてGOALだった。

教師への誤差は三条件とも減ったが、異なる教師のMSEを棋力順位にはしない。C/Sの一般的優越、劣位、等価、旧敗戦原因や自動昇格を認定しない。元モデル・既定は維持する。

- [有限対局・区間・時計・深さ・例と費用](final-analysis-v1/report-ja.md)
- [同じ更新列でのfit・教師・層別保存解析](fit-teacher-analysis-v1/report-ja.md)
- [元FileRef・受入れ・保存対応](receipt.json)

教師10024行ずつ、paired3fitの30104 draws/118 updates/tail152、共通stream76f6467b、fit+native1521558行、対局1072837747 charged nodesを保存した。8元RAWは分析者が各一度だけstreamし、二つの固定family bootstrapも各一度だけ実行した。元FAILED・S19 failed attempted rows/kernel UNKNOWN、内包時計の非加算、physical NNUE/continuous RSS/全費用UNKNOWNを残す。次のfit・教師選択・対局をこの結果から自動発行しない。
