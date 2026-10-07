# 事前確保入力と正本のCriterion比較

今回の比較では、事前固定した「明確な退行」の条件を満たす探索局面は０／５だった。詳細プロファイルの条件は成立せず、プロファイルは未実行。速度改善の採用も行わない。通常headの一時確保を避ける設計資格と、探索全体の速度判断を分ける。

正本Aはallocating residual60d／実行画像c6fb、Bは凍結済みborrowed input scratch fab07＋production AlphaBeta0d4／実行画像f151。Bは探索ごとに所有したscratchを再用し、headを測るときも事前確保の連続bufferを実際に借用する。一回ごとのsetupをnormal headとして測っていない。FT・TT・WallMaps・sortの過去候補を混ぜず、重みは旧固定BEST c0ec、Scalar／FT32 H32／５合法履歴・depth3・同一TT設定を保持した。

変更されたbench呼出しを先にA/Bで資格確認した。18プロセスすべての５局面で値bits、Action、PV、完了depth、stop、全23仕事カウンタ、保持量、親履歴が既資格と完全一致した。Bのborrowed headとallocating referenceのbitsも一致。受入幅・P1P2・full/delta・undo・error/cancel・非alias・通常head allocatorの既存独立証拠は、今回と同じ凍結source/dependency SHAを確認して再用した。古い全suiteを再実行していない。

| 局面           | head相対時間 | setup/dropを含む探索全体の相対時間 | 明確な退行B数／４ |
| -------------- | -----------: | ---------------------------------: | ----------------: |
| initial        |       -1.67% |                             +0.78% |                 0 |
| opening        |       -1.26% |                             -0.17% |                 0 |
| walled-midgame |       -2.66% |                             -1.25% |                 0 |
| jump-p2        |       -2.55% |                             -3.28% |                 0 |
| endgame        |       -0.68% |                             -1.65% |                 0 |

上表は、各Bを前後のAと比べた８つの標準Criterion相対平均推定値の中央値という記述値。負は時間減、正は時間増で、統合された信頼区間ではない。全部の点推定値と各95%CI／標準判定はsummary.jsonに残した。initialの探索は点推定値で僅かに遅く、他４局面は中央値では速い。jump/endgameには一部の有意な改善もあったが、４つのBプロセス全体にまたがる一貫した利益とは認定しない。headでもブロック間の逆転を残し、局所利益を全体・棋力へ一般化しない。

測定順はA0 B0 B1 A1／A2 B2 B3 A3の２ABBAブロック、８独立計時プロセス。各IDは50サンプル／１秒warmup／３秒measurement target。全ブロック終了後の８個の標準loaded analysesで各Bを両隣Aに比較した。50サンプルは50独立プロセスではない。明確な退行は、各根で３／４以上のBについて、両隣Aに対しCriterionがregressedと判定し、相対平均の95%CI下端が+1%を超えること（両順序方向含む）。全体退行は４／５根以上。この事前ルールを結果後に緩めていない。

head timerはfull FT／workspace setupを除外。cold search timerは実production evaluatorのroot FT、探索owned scratch、player/TTのsetupとdropを含む。モデル読取、合法履歴再生、起動時oracle、標準統計解析はsample timer外でwhole processに含む。各計時プロセスは46.63〜48.77秒だが、Criterionが反復数を適応的に選ぶため、そのprocess wall比は固定仕事の速度比ではない。head/search時間とprocess/controller全費を混同しない。

whole controller398.41771834297106秒、実head calls448,484,934、exported delta updates155,224,468。loaded analysesも実５局面のpreflightを実行した費を含む。内部FTの未export操作数はUNKNOWN。２software試行2.306071889＋31.841320472秒を含む既Criterion全11controllerのknown合計636.060203123022803秒。nested clocksを加算せず、管理・LLM・過去UNKNOWNも０にしていない。旧CLI失敗と古い少数計時の不支持・退行を成功化せず保持する。

全18 bench直接wait／guardian worker wait／controller cleanup[]を確認、記録科学PID/start不在、正本sourceと共有ELFを復元SHA確認。CPU0,1／RAMfamily2GiB／GPU0。sampled family RSS122,507,264B、owned output peak1,433,600B；continuous peak保証ではなくshared target growthはNULL。Root256MiB内の受入forecastを再用、全walk／旧資産削除／UNKNOWN解放はしない。新生成working blockだけ、全memberのbyte/SHAをlossless gzipに復元確認してから予定寿命どおり再用した。

速度採用・API/main統合はRoot判断へ返す。明確な退行を再現しなかったため、その原因を断定する詳細プロファイルは実施しない。heap回避の原則は維持するが、断片化・latency・棋力への一般的な改善は未計測。学習担当は明示pauseのまま起こしていない。今回source/画像/rawは保存し、新candidate・追加job・数学変更・profile実行を追加していない。
