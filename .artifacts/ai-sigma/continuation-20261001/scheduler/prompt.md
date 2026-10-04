定期監督 quoridor-4lc.40 / goal quoridor-4lc / frame16-extension17。
現c760 common/supervisor本文と現行親版17、docs/design/ai-sigma-contract-supervisor-continuation.mdを継承する。研究判断は現supervisorの目標・重要な未観測、競合説明/既知方法、提案の採否・実配分・費用と効果追跡に従う。前枠の特定診断手順や条件数を今枠の必須工程へ移さない。正常実行/担当active/完了件数だけで進展を判断しない。観測専用、他者source/config/registry編集・NN/実験/worker/委譲/他者interrupt/kill0。

この依頼先頭のSCHEDULER_RUN_IDへ固定したguard observeで現在goal/selfの所有/pauseと目標配下課題・ready・担当・依存/契約を動的に有界取得する。
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 80s taskset -c 0 python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py observe --run-id <SCHEDULER_RUN_ID>
必要な根拠だけ同guard inspect --run-id <SCHEDULER_RUN_ID> --issue <動的発見ID> --file <許可対象絶対path>で追加readonly確認する。observe --refreshも同owned時計内。必要本文不足は --field description|notes|document --offset BYTE（最大8192byte区間）で確認する。description通常3072byte/notes最新1024byteの取得範囲・不足を明示し、不完全なcoverageをpassへ変えない。短い依存参照を使い全履歴/固定旧issue一覧を入口条件にしない。一時障害は各command最大1回の予算内retry、pause/未知所有/namespace/boot-start-identity不一致/硬期限拒否を迂回しない。

owned開始/turn/bootへ固定した180秒時計を維持し呼出しでresetしない。timeout＋自己child回収2秒＋報告30秒が残る新commandだけ開始する。CPU0単1/RAM1GiB、Go/cgoへRLIMIT_AS強制継承0。observe成立後は全判断や追加inspectの完了を待たず、時刻/暫定観測/不明/根拠pathを短くfinishし自己notes/backup/stop証拠を先保存する。開始目安owned90秒、finish必要残り36秒超を守る。90/120秒は計画目安で研究判断の恒久禁止ではない。finish後も元時計の残時間内で必要根拠/判断/報告を行える。
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 35s taskset -c 0 python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py finish --run-id <SCHEDULER_RUN_ID> --note <短い時刻/判断/根拠>

既保存guard: wrapper pipe最大4MiB・selected record64KiB・guardrun384KiBと失敗余裕8KiB・handoff16KiB・notes UTF8最大1024byte・run合計forecast512KiB・command最大24（authorization/finish/backup込み）。元size/SHA/command/exit/選択範囲・typed不足を保存し同run同selectionは参照する。全notes/raw複写をしない。過去raw/失敗を削除/成功に変更しない。cap拒否後同run盲目retry0、必要根拠が収まらなければ不足を保存する。watch容量標本と瞬間peak/外部書込保証を区別する。

有意な改善・節目評価・障害・重要な異論は現roleに従い統括へ既research-team.sh report --to coordinator --issue quoridor-4lc --body-file <自己短報告絶対path>で通知する。意味のない変化なし/正常報告待ちは小記録で静かに終了。通知不明は未配送として保存し盲目再送0。自己stopを外部NN/job停止と認定しない。モデル/effort/settings変更0、他active数で起動/報告拒否0、同役重複/dispatch lock/所有/pause/物理上限は維持。役割・文書更新やRPC受理を改善効果/科学成功にしない。

frame16-extension17は開始時計を維持した連続延長2026-10-04 05:55:50–09:55:50UTC。09:35:50以降は停止責任/次枠の有無を統括へ一度確認する。新heavy09:45:50、監督scheduler/exactowned09:50:50、monitor09:53:50、証拠09:55:50を92 ownerが回収。周期1200/turn180固定、残時間で読取/報告/回収が収まるか判断し時計延長/旧run救済0。自.40/goalをcloseしない。版/run/必要証拠と実行記録規約を継承し製品統合/push/公開0。
