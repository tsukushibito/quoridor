# SIGMA-SCHEDULER-RECOVERY / quoridor-4lc.44 / 試行1・契約1
steward → coordinator。契約030fdeb0…5b237/継続859bb777…a81a2全文継承、ready/show goal/.38/.44非pause後に自.44のみclaim。.42は不足付き限定受入れをnotesへ残しclose、追加検証0。

問い/原因: 旧monitorの10:24:40.425378 state.json FileNotFoundErrorと、10:24:42.768238のstop成功/ownedなし、旧PID不在を確認。16:55到達ではなく異常早期停止。旧watchは単発read例外で終了していた。main atomic_jsonは既存stateをos.replaceし、通常この方式だけで欠落を説明しない。隔離fixtureで既存atomic置換200回/読取にも欠落は再現せず。旧例外にstack/syscall/削除actorの証拠はなく、原因は未確定。ordinary atomic-write原因/外部削除/FS visibility/.42因果を断定0。

変更: tools/ai-sigma-scheduler-monitor-recovery/の自己copy。旧source/stop/events/.42成果を保持、主code/registry/6定義/config/prompt変更0。state/events読取を最大5回・0.1秒間隔・2秒retry枠で記録し、一時障害から復帰。持続/破損/binding/identity/owned不明はfail-closed。正常stateは既存stop wrapper、state不明時はstartupで保存した自schedulerのboot/PID/starttickを再照合しpidfdからSIGUSR1だけ送る。未知/再利用PIDはsignal禁止、owned確認不能はunknownを保持。旧証拠へstopを書かず新版runへ保存し、無限retry/盲目restart/send0。

検証: 10隔離診断（欠落/破損一時・持続、binding/identity/所有異常、atomic置換、signal拒否）と、実自己copy関数の3隔離mock（正常read/未知identity/既知identity限定回収）成功。liveへの故障注入・実signal・NN/build/取得/同期/学習/GPU/対局/委譲/他者kill0。隔離fixture内のfault操作のみ、旧証拠削除0。詳細verification/copy-verificationとwatch-copy.patch。

復旧: 同config/runtime/target supervisor/.40/契約/1200周期/閾値2/global3/16:55を維持してvalidate→start→status/eventsを確認。prompt最終f818745f4cdae353fa2d5d27771209c292ed157ff1da91a3b074b00933590eed固定、config d85295ca…30efb。scheduler1079010/starttick10458023、monitor1079039/10458080、boot共通/CPU0。10:48:00初回はactive_limit skip、実点検成功ではない。next11:07:58.784161UTC、周期早送り/強制turn/steer0。新epoch前の旧初回dispatchを新点検にしない。新版run live-daa5b686-937b-4522-953d-83993dfaf9e4。後続liveの本文/90・120・180gate/全期間運用は未観測。

資源/停止: 19原input前後hash一致。新allocated192,512B/32MiB、合算owner範囲標本peak864,256B/112MiB、既存128MiB内・追加予約0/累積12GiB維持。背景RSS標本peak49,967,104B、自己診断約16MiB。瞬間同時RAM/全ホスト無負荷/正確全研究増分は未認定、旧課金と欠測を減額0。10:52:49 short-jobs-stopped.jsonを本文前保存、短期7identity稼働0。予備読取/copy-builder親PIDの一部は欠測、同期exit成功は保持。以後準備書込停止、背景運用書込は別責任として継続。

引渡し/再現: 新tool README、.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY/ のinputs-before/recovery-observed/recovery-start/cause-assessment/短期stopと新版runのbounded-read/events/process/終了JSON。元sourceと19重要入力は不変。steward .38を同owner .44が補修、16:55 owned scheduler/正確turn停止確認、16:58 monitor回収、17:00終了を保持。応答だけで全job停止認定0、外部NN停止は各owner。採用判断は復旧準備の独立受入れと後続点検の別照合。.44受入れ待ちin_progress、.38/.40/goal close0。原raw/失敗/旧逸脱/旧32局・Sigma未達/新対局0を保持。再生成可能なのは新mock fixture等だが今回は整理・旧証拠削除0。
