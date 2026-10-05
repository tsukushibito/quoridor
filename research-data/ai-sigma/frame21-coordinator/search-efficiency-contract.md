# frame21 探索高速化を教師生成効率と学習利益の原因へ結ぶ
Owner critic既saved/model-effort不変。ready/show本人assigned/pause確認→claim。役名は実作業を制限しない。この課題は独立の実装・費測定担当で、終了後算術だけに限定しない。

mainは正本。初期main cwdで現役Rust core/ai/runnerと生成pumpを読取。並行コード変更は保存方針読取後manage_worktree.shでmanaged .worktree/frame21-searchへ分離（branch codex/frame21-search、main現HEADから、旧ai-sigma WT変更0）。worktree作成は通常許可内、全source/Gitindex単一統合担当はcoordinator、本人commit/index操作0。solewriteこのWTの crates/quoridor-core/src/、crates/quoridor-ai/src/、必要性能検査・汎用benchmarkのみと research-data/ai-sigma/frame21-search-efficiency/、docs/reports/ai-sigma-critic-frame21-search-efficiency.md。main既source編集0、experiment266新runner diagnosticと分離。runner sharedpump修正が必要なら具体pathを統括へ返しowner境界を確定、重複編集0。

主目標は強いNNUEを効率良く学習・探索すること。QF1/教師の情報不足の調査を待たず探索費の実仕事を並行。まずαβのlegal生成/距離/clone/make-unmake/NNUE/TT/orderingとMCTS教師生成search/pump/evaluationを分け、同一coreが両者へ効く実費を選ぶ。必要プロファイルは最大1有力変更を選ぶために絞る。BFS/cache再用、合法壁検査等はsourceと同仕事量実測から選び、inclusive timerを二重BFS・排他的律速へ変換0。最大1初期異論として現266モデル/尺度/対照の原因判別不足も返せるが、全稿承認gate0。

09:10 early本人開始/実sourceから選んだ支配費と改善候補、09:25まで最初実profileか未成立具体理由を返す。独立WTで1介入の実装→meaningful core RuleA/history/合法/終局/距離/parent復帰・数値parityを確認→同prefix/seed/同depth-nodeと同K教師生成を比較する。新モデル/学習/対局0、固定仕事NNforwardは費測定に必要分だけ（元評価器/教師の品質条件不変更）。CPU2single/RAM2GiB guard1.75/GPU0、計算計4logical/aggregateRAM8GiBを守りnative現物headroom/actualforeignCPU/現在frame21 loaded/owner/子終了を入口でfreshadmit。LLMactive/owned非nullだけをCPUbusy gateにしない。266計算CPU2と合計4だがtiming比較jobを重ねない。実profile/修復/測定全attempt science900s、最多4job各180s、compile/test CPU2計300sを別計数、nativeNN250000/processed500000上界。NN実計数不可ならUNKNOWNと上界charge、0を捏造0。新GPU0/ORT_DISABLE_TELEMETRY=1 frameworkimport前、deps/toolchain更新0。

同仕事・同品質・同K/seedと有効教師行/全job秒、αβ完成depth/全timeを分ける。MCTSのrandom/並列batch順が変わるなら品質同一を勝手に認定せずcounter/差・局面分布を残す。αβ速度をMCTS倍率にしない。profiler/hostJIT/cache/coldwarm順を記録。観測する速度利益と実装検証費、特徴追加による非局所更新費を将来NNUE設計へ返す。有効利益がない案は保存・不採用、全面TT/全移植の自動追加0。

保存budget:source/results forecast3MiB/guard3.5MiB、最多4MiBを旧本人241/246/251等の確認unused予約から移転しfresh current/必要Git/tmp重複を記録。不足なら実必要量＋同pool確認unusedを返し統括が移転、旧小guardを必要改善の拒否根拠0。managedWT/source/buildcacheは既研究aggregate12GiBにfresh actual/forecastで含め、既release/sharedCargo cacheを再用するが旧保管UNKNOWNはfreeとしない。新ダウンロード/モデル/共有環境更新/削除0。再構成不能入力とuncommittedsource保護、旧モデル/ホールドアウト173/198読取0。

結果が有望なら検証済path/patch/source停止/版/条件/全費を統括へ渡しmain統合・266への版採用を判断。同測定の途中でmainへ混ぜない。新heavy10:27:54まで、実science/test10:28stop、source10:25stop、save10:32/全枠10:37:54。既background jobID→notes→Idle→完了一度、盲目poll/retry0。usagefailed再発はexactfailed保存、モデル変更等回避0。本人close/backup、主最高目標未達維持。
