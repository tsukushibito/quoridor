# 根のvisit分母の方法補足

quoridor-4lc.28 / SIGMA-ROOT-SELECTION-ABLATION / 試行1 / 契約版2（方法補足）。原契約版1・原run/報告・manifestは不変保存。この補足は原処理01:25/提出01:35・CPU0/RAM1/new32MiB/global04:00の内側でだけ実行する。資源/期限拡張0、追加NN/全MCTS/棋力対局/製品source変更0。

統括の版1指定N=sum(edge.visits)は元node.visitsと一致しなかった。元simulateは初回根評価でleaf root visitsを1増やし、後続path backupでもroot visitsを増やす。今回765正常completed根はedge訪問和=sim−1であり、元node.visits=sim=edge訪問和+1というsource上の復元条件を先に確認する。元root visitsの直接rawがないなら、これはsource+completed statsによる復元で、直接観測ではないと明記。terminal/no checkpoint/errorの根はこの条件へ無理に当てない。

最終finishはnode.visitsを使わないため元765/765のgateを保持可能。版1のC28/sqrt9/scoretie117等はN=edge和を固定した反実仮想という限定結果のまま保持し、元実装の次select復元と呼ばない。統括自身の方法指定の差を報告者の実装失敗としない。過去棋譜/.26candidate/kernel/条件/成績変更0。

新出力は同artifact内 revision2-node-visits/ と別report docs/reports/ai-sigma-hypothesis-root-ablation-v2.md のみ。元27重要input+版1原結果のhash前後を確認。既存diagnostic binary/scriptを先読取し、inputのNのみnodevisitsへ変更した同一プログラムで1回再実行を優先（新compile不要）。原sourceどおりbaseline sqrt(node.visits+1)=sqrt(edge和+2)。Cだけ1.5→1、sqrtだけ+1→+0、score同値tieだけseed→firstを各別対照として全765/accepted764/matched194で再集計。その他finish/order/FPU人工例の再実行は不要。rootactualActionは再び全765確認、baseline選択は今も観測された次Actionでなく「元関数を最終状態に適用した仮想次選択」。変更後の全検索/棋力推定なし。

01:22以降新job0・01:25処理停止/01:35提出を保持、既存stopJSONを原証拠として残し新stopJSON/PID0を先保存。失敗・欠測・瞬間RSS/初期ledger限界も保持。十分な残時間がなければ方法訂正と未実行を返し延長0。自.28のみ作業、本人closeは補足を含む統括受入れ後。ready/show目標/.28、pauseなしを確認してbackup/report --issue quoridor-4lc --to coordinator。再実行を実際に進め、旧と新の operational N を分けて返す。
