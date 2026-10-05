# SIGMA-SUPERVISOR-ROLE-REVIEW / quoridor-4lc.61（親依頼.58）/ 試行1・契約1

steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6 → coordinator。ユーザー明示依頼 .58 の実適用を既存scheduler/monitor所有者へ委譲する。親継続版2 SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。終了Oct2 01:00UTC/重job00:50/監督00:55/monitor00:58、CPU/RAM/LLM3/累積12GiBは不変。旧.38/.42/.44/.53契約/raw/失敗を上書きしない。

新責任: supervisorは停滞か、現在の役割定義/分担の見直しが必要かを自律判断し、根拠・不確実性・変更案・期待効果・検証方法をcoordinatorへ報告する。新知見の増加、失敗で仮説が絞れているか、同じ修復への集中、代替仮説担当の機能、担当集中/引継ぎ/独立検証負荷、目標必須条件と特定実装由来の条件の混同を短い観点として記載。固定失敗回数だけで判断せず、無用な定期文書/毎回複数案/全証拠再計算の義務を増やさない。必要性判断/提案=supervisor、採用・課題配分・所有者を通じた安全な適用=coordinator、変更後効果点検=supervisor。役割改定で予算/製品範囲/実験許可は増えず、監督自身のconfig変更・worker直接起動は引き続き禁止。末尾17:00固定表記を現継続正本参照へ変更。

write owner: 今回だけ主checkoutとai-sigmaの .agents/research-team/roles/supervisor.md、および docs/design/ai-research-team.md の監督運用追記、必要な専用supervisor運用文書/prompt/contract/hash binding と registryのsupervisor entryだけをstewardが安全適用する。common/他5role・主実装・モデル/effort・製品/lockは変更0。rootは未追跡主supervisorを未変更、現在統括もこの範囲を書かない。同範囲の他writerを確認し、before bytes/hashと旧registry/prompt/state/eventsを自己runへ保全してから更新。新tools/ai-sigma-supervisor-role-review/、continuation-20261001/SIGMA-SUPERVISOR-ROLE-REVIEW/、docs/reports/ai-sigma-steward-supervisor-role-review.md が自成果物。

既owned turnを読取確認し、dispatch lockと既存stopでschedulerだけ一時停止/owned無しを確認してroleを改定する。未知/他研究turn割込0。保存supervisor同threadへdeveloperInstructions=common+改定role+既runtime suffixを明示thread/resumeして適用（主CLIのrefresh choicesにsupervisorが無ければ既AppServerの同方式を使う専用helperで可、モデル/effort override0）。保存threadの設定/definition hashとregistryを再取得し照合、source変更だけで完了しない。promptは180秒/新admission90/読取120の既guardを維持し、判断観点を予算内へ追加。scheduler config/period1200/threshold2/target/.40/end/turn180は不変、監督role definition digestを整合させる。watch期待hashは同ownerで新runに更新して再start/reload・live state/hash確認。未知状態ならfail-closed、過去異常停止を今回正常へ書換え0。

新周期の自然dispatchまで無理に待たず、保存session適用RPC/registry/validate/config/prompt/生stateに反映された証拠と正確thread IDを先提出する。supervisorからの受領を得る場合はglobal3を守り、短いackのみまたは次自然turnから全文取得、強制研究turn0。保存sessionの実developerInstructions読取可否を区別、digestだけを本文受領と呼ばない。後続自然turnで新prompt/body一致・判断/効果点検の確認責任を長期ownerとして保持し、今回準備と全期間成功を分ける。

CPU0/RAM1GiB・new16MiB guard14は既steward128MiB/combined112内、追加予約0。UV_NO_SYNC/OFFLINE/PYTHONDONTWRITEBYTECODE、Go AS制限継承0、専用TMP・短いtooltimeout、PID/starttick/exit/RSS/容量・旧新hash・RPC原応答を保存。NN/build/取得/依存同期/学習/GPU/対局/委譲/他者kill/旧証拠削除0。実験 .59 はCPU2別sourceで継続し、本変更待ちで全研究停止しない。処理受領25分または14:55、提出35分または15:05の早い方、新job5分前停止。自己短期stop/hashafterを本文前保存、長期scheduler/monitor責任は00:55/00:58維持。自.61のみclaim、.58は統括が保存適用証拠/担当受入れ後close、backup/report。旧NI未立証/goal未達維持。
