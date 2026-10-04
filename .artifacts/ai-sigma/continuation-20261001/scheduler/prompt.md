定期監督 quoridor-4lc.40 / goal quoridor-4lc / frame18。
現c760 common/supervisor本文と現行親版18、docs/design/ai-sigma-contract-supervisor-continuation.mdを継承する。研究判断は現supervisorの目標・重要な未観測、競合説明/既知方法、提案の採否・実配分・費用と効果追跡に従う。前枠の特定診断手順や条件数を今枠の必須工程へ移さない。正常実行/担当active/完了件数だけで進展を判断しない。観測専用、他者source/config/registry編集・NN/実験/worker/委譲/他者interrupt/kill0。

この依頼先頭のSCHEDULER_RUN_IDへ固定したguard observeで現在goal/selfの所有/pauseと目標配下課題・ready・担当・依存/契約を動的に有界取得する。
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 80s taskset -c 0 python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py observe --run-id <SCHEDULER_RUN_ID>
必要な根拠だけ同guard inspect --run-id <SCHEDULER_RUN_ID> --issue <動的発見ID> --file <許可対象絶対path>で追加readonly確認する。observe --refreshも同owned時計内。必要本文不足は --field description|notes|document --offset BYTE（最大8192byte区間）で確認する。description通常3072byte/notes最新1024byteの取得範囲・不足を明示し、不完全なcoverageをpassへ変えない。短い依存参照を使い全履歴/固定旧issue一覧を入口条件にしない。一時障害は各command最大1回の予算内retry、pause/未知所有/namespace/boot-start-identity不一致/硬期限拒否を迂回しない。

ユーザー明示によりowned turn時間上限はnullであり、180秒経過のみで終了・interruptしない。owned開始/turn/bootと14:28:18UTCの運用endを固定し、呼出しで時計をresetしない。前turn activeなら次周期はskipし二重開始しない。timeout＋自己child回収2秒＋報告30秒が残る新commandだけ開始する。CPU0単1/RAM1GiB、Go/cgoへRLIMIT_AS強制継承0。observe成立後は全判断や追加inspectの完了を待たず、時刻/暫定観測/不明/根拠pathを短くfinishし自己notes/backup/stop証拠を先保存する。finish必要残り36秒超と子回収/報告余裕は絶対運用endに対して確保する。早い短記録は推奨で研究判断の時間上限ではない。finish後も元時計の残時間内で必要根拠/判断/報告を行える。
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 35s taskset -c 0 python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py finish --run-id <SCHEDULER_RUN_ID> --note <短い時刻/判断/根拠>

既保存guard: wrapper pipe最大4MiB・selected record64KiB・guardrun384KiBと失敗余裕8KiB・handoff16KiB・notes UTF8最大1024byte・run合計forecast512KiB・command最大24（authorization/finish/backup込み）。元size/SHA/command/exit/選択範囲・typed不足を保存し同run同selectionは参照する。全notes/raw複写をしない。過去raw/失敗を削除/成功に変更しない。cap拒否後同run盲目retry0、必要根拠が収まらなければ不足を保存する。watch容量標本と瞬間peak/外部書込保証を区別する。

有意な改善・節目評価・障害・重要な異論は現roleに従い統括へ既research-team.sh report --to coordinator --issue quoridor-4lc --body-file <自己短報告絶対path>で通知する。意味のない変化なし/正常報告待ちは小記録で静かに終了。通知不明は未配送として保存し盲目再送0。自己stopを外部NN/job停止と認定しない。モデル/effort/settings変更0、他active数で起動/報告拒否0、同役重複/dispatch lock/所有/pause/物理上限は維持。役割・文書更新やRPC受理を改善効果/科学成功にしない。

frame18はユーザー明示の新4時間枠2026-10-04 10:33:18–14:33:18UTC。14:13:18以降は停止責任/次枠の有無を統括へ一度確認する。新heavy14:23:18、監督scheduler/exactowned14:28:18、monitor14:31:18、証拠14:33:18を92 ownerが回収。周期1200/turn上限null、残時間で読取/報告/回収が収まるか判断し時計延長/旧run救済0。自.40/goalをcloseしない。版/run/必要証拠と実行記録規約を継承し製品統合/push/公開0。
