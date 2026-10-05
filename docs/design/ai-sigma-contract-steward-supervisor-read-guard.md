# SIGMA-SUPERVISOR-READ-GUARD / quoridor-4lc.42 / 試行1・契約1

担当steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6、統括01a0f31b-3409-75f2-a30e-453a50484f94へ報告。[継続枠](ai-sigma-continuation-20261001.md)全文を継承（SHA859bb777836cc0683e1ad7d1763a71fda60c75d2d6391290cef28771589a81a2）。目標同等未達、旧32局/逸脱保持。ユーザーの詳細委任下の運用修正でありpause解除/研究資源追加ではない。

問い: 次の監督点検で新metadata読取を早めに止め、開始時刻と環境を確認できるか。critic .41の初回9command/限定点検を支持しつつ、120秒gate不足(+11.650416秒推定、OS明示stamp欠測)を保持する。旧180秒以内を全面遵守としない。入力 docs/reports/ai-sigma-critic-scheduler-live.md SHA4f7df41f53f161dc041cf31c80464aa54411ba5f9089f1fceb5be9cf6136ea16、CRITIC-SCHEDULER-LIVE/summary.json SHAa7566b05cec5188fbe2aefb5227c026f22ead3375b0f493e61903bb35ee1884d、統括限定受入れ報告。

場所/worktree/branchはai-sigma/codex/ai-sigma。書込ownerはsteward一人。新tool tools/ai-sigma-supervisor-read-guard/、新artifact .artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-READ-GUARD/、報告 docs/reports/ai-sigma-steward-supervisor-read-guard.md、および既存運用scheduler/prompt.mdのみ編集可。必要な補足契約を新artifactへ保存可。主checkoutのscheduler/team実装・registry・6role定義、親契約/旧.40契約、旧証拠、研究source/製品/lock/UI/M2は変更0。旧prompt/config/hash/原inputを編集前に保存する。

制約と期待動作: 一つのrun/turn/owned開始に結び付く固定締切を用い、再呼出しで時計をリセットしない。新読取開始はowned開始から90秒まで、読取処理は120秒まで、終了報告/自己notes/backupは180秒turn内。安全なmonotonic換算と明示開始/終了stampを持つ有限metadata実行guardを作る。run/turn不一致、開始不明、既期限はfail-closed。コマンドはBeads wrapper/role status/既存運用metadataに限定し、UV_NO_SYNC=1/UV_OFFLINE=1/PYTHONDONTWRITEBYTECODE=1/CPU0を明示。最初に必要metadataをまとめて読み、終盤の再点検を避ける。期限/timeout時は自己childのみ回収し、他者turnやscheduler/watchをkillしない。Go/cgoへ1GiB AS制限を継承した旧失敗を繰返さず、RAMはRSS予算として観測する。方式詳細は担当判断、必要最小限とする。

promptは最初のバッチ観測をguard経由にし、新読取の遅い追加を禁止する。LLMが別toolを直接使う全経路の強制隔離は本guardだけでは証明できないため、scripted-pathの成立とwhole-turn遵守を区別する。締切後は新metadata取得をせず、既存観測から終了する。新研究/配分/他issue操作/無意味な統括通知0。自己.40のclaim/notes/backupを必要な範囲で扱うが、同期Beads副次書込量と終了時間の限界を保持する。

検証: 期限前/同時/後、誤run/turn/開始不明、run再呼出しによる締切非延長、timeoutと自己child回収、環境/affinity/明示stampを小さいmock/標準toolで確認する。live supervisor turnは強制起動/steerしない。既存runtime /workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/ の同target/.40/契約/1200周期/閾値2/終了16:55を維持しreloadする。受付のみで成功とせずreloaded event・prompt/config hashと次回時刻を保存。reloadによる次周期移動は保存し、早送りしない。既存ownedturnがあれば完了後に反映、誤ったturn中断0。次のlive開始/内容/90/120/180 gateは運用owner .38が別証拠として観測する。ここでは未観測を完了扱いしない。

予算: CPU0単logical、RAM1GiB（同owner .38 scheduler/watchと合計、sample peak限界保持）。新32MiB以内を既存steward128MiB未使用予約内で使う、combined guard112MiB/累積12GiBを維持、追加予約0。NN/GPU/build/取得/依存同期/削除/追加委譲/新対局0。標準Python/Nodeの小さな診断のみ。処理は受領25分以内または10:25UTCの早い方、新jobはその5分前停止、提出35分以内または10:35UTCの早い方。17:00枠/16:55運用停止責任は延長0。.38の既存背景運用は別責任として継続し、全自己job0と混同しない。

ready/show目標/.42/.38/pauseを確認、自.42だけclaimする。作業終了前に短い自己job停止をPID/starttick/exit/RSS/storageとともに文書より先に保存。失敗/未成立/旧逸脱を保持、原hash前後確認、backup/report。新guardとreloadの限定準備受入れ待ちin_progress。本人closeは統括受入れ後。.38/.40/goalをcloseしない。変更を無条件の全文書遵守、速度、棋力、Sigma到達と認定しない。
