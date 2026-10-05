# frame20 / 248 距離極値の由来とclip→tanh有限対照

2026-10-05。goal quoridor-4lc、hypothesis248。新独立課題の一回NN0計算は全16条件完了。旧244のjump fixture失敗（exit1、processed4、16全NOT_RUN、MAX1消費）は不成立のまま保持し、旧source・期限・科学結果を変更していない。

受付01:21:42、claim/static開始後、新私有sourceを結果前Git9808f1175d5d1c973e6568d513c7a623dca4b01eで固定。jumpのActionは単位方向であり、_pawnDest及びnextのP2着地点が2cell進むことへ検査を修正した。科学は01:28:10.059532–01:28:12.271930 UTC、CPU4単1、NN/GPU0、2.206670280秒、family peak293470208B。processed63178/65536（fixture6込み）、6fixture PASS、16/16 COMPLETED、exit0と専用task/schema目的束縛PASS。全子wait・child/managerの現在PID-starttick不在を確認。科学再実行0。

同239機械選択4prefix、全合法rootchild、depth1/2、Dclip/Dtanhを変更せず比較した。全max/min同値極値を列挙し、非極値は由来集合へ足さず、negamax各edgeの符号とterminalWin/Lossを伝播する。由来件数はtreeの極値leaf出現数であり、独立局面数ではない。旧240のclip全8列はAction別数値最大差0、結果前abs1e-7+rtol1e-7に一致した。

| case | depth | clip最大値/argmax数 | tanh最大値/argmax数 | root極値由来 |
| --- | --- | --- | --- | --- |
| 0 | 1 | -1 / 94 | -.782230973 / 4 | 非終端clip飽和 |
| 0 | 2 | -1 / 94 | -.868419111 / 3 | 非終端clip飽和 |
| 1 | 1/2 | .038688969/.060382154 / 各10 | .038669676/.060308877 / 各10 | 非終端非飽和 |
| 2 | 1/2 | .038688969/.060382154 / 10/12 | .038669676/.060308877 / 10/12 | 非終端非飽和 |
| 3 | 1 | -.555737615 / 1 | -.504808068 / 1 | 非終端非飽和 |
| 3 | 2 | -1 / 3 | -1 / 3 | terminalLossのみ |

case0の全94 exact root値-1は終局伝播ではなく非終端clip順位消失だった。depth1のleaf rawは1.051093–1.546449、depth2の極値leaf rawは-1.821969–-1.029400。tanhでstrictfirst Actionが11→19/134へ変わる。ただしdepth2の旧source Action11のtanh gapは5.96046448e-8（f32一ulp）に過ぎず、厳密tieの縮小を実質的な手改善へ読み替えない。case1/2の同値集合及びstrictfirstは不変。case3 depth2の-1は各rootchildがterminalLossへ至る極値で、tanhでも解消しない。root値-1だけから由来を断定できなかった旧UNKNOWNを、この有限horizonの由来記録で区別した。深い真値は未確認。

Dはq.input既STM距離/80をそのまま使い、diff=f32(dopp-dself)、u=f32(f32(a)+f32(f32(b)*diff))、clipは[-1,1]、tanh=f32(Math.tanh(u))。終局±1・draw0を先処理し変更しない。係数/入力/sourceSHAはpreregister.json、各childのpreclip/clip/tanh/range/witness/signはresult.json.gzに保存。tanhの有限fixtureでf32端点±1が可能と確認しており、一般の非終端端点不達を保証しない。GOAL優先、ply200draw、P2jump/HVwall/親history復帰、third-repetition exclusionを有限確認した。no-legal fallbackはmock検査であり全合法局面の再認証ではない。

次の最大1案はDclip対Dtanhの同wall paired小arenaを結果前に固定すること。今回D基準の順位消失はcase0で支持されたが、case3の終局/horizon問題やNNUErootmean教師→minimaxleafの意味差は説明しない。NNUE再学習より先に、同一terminal/history/alllegal/order/時計でDの変更だけを判別し、基準側の交絡を棋力経路で確認する。既私有arenaへ将来の専用D modeを薄追加、source/評価式parity検証10–15分、結果を見る前のfresh4opening×先後交換8slot、各100ms/手・120秒gamecapで科学最大16分、管理約5分を見積もる。UNKNOWN/全slotを保持し、小標本を一般強さ認定へ広げない。期待利益はclip飽和時の順位解像度で、勝率利益及び実wall費は未実測。改善不支持ならD変更の順位を下げleaf-target/historyの検証へ戻す。これは次の配分案であり新arena・NN・学習を起動していない。

再現入口（新配分/新scopeが必要、現在MAX1済のlauncherを再起動しない）: taskset -c 4 python3 -B tools/ai-sigma-frame20-distance-provenance-repair/launch.py。actual argv、sourcehash、currentloaded247の24hash、producer242 source9/payload7・background cleanup・newstop、244/246 exact不在、自然ownedNone/quiet648.7秒、RAM/storageの直前admissionを保存。全host/未来無競合保証ではない。label/モデルPT/Torch/teacher/test/173は未読、追加依存0。

科学正本とmetadataはresearch-data/ai-sigma/frame20-distance-provenance-repair/、sourceはtools/ai-sigma-frame20-distance-provenance-repair/。旧2441MiB/旧費UNKNOWNは保持、新1MiB予約のみ使用。forecast/actualstorage/Git復元/close/backupの最終receiptを同scopeに保存し、最高棋力goalは未達のまま統括へ引渡す。
