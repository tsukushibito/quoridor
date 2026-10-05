# 104.1 セッション数制限撤廃

標準send/report、scheduler、実92 scheduler/reportから他role/rootのactive数による拒否と入場用全session読取を除去。宛先だけ確認し、activeへ正確turn/steer、idleへstart。同役二重起動、dispatch lock、pause/所有/digest、期限と正確owned回収は維持。互換CLI引数は無視、JSON `max_active_sessions` は新設定null・旧正整数も制限に使わない。

現行枠版6、common/supervisor/team設計・監督prompt/契約と92有効契約2を整合。main専用schedulerを研究側へ実体複製していない。coordinator所有dispatch.py/103には書込0。CPU4/RAM8GiB/保存12GiB、周期1200/turn180、05:39:12重job・05:44:12監督・05:47:12monitor・05:49:12終了は維持。

fakeAppServer標準36試験と実92コピー4回帰がpass。他役3以上activeでもidle task/report/監督start、active宛先steer・二重開始拒否、pause/期限/正owned停止を確認。6registry digest一致、coordinator/hypothesis/critic/supervisorはidle恒久resume成功、experiment/stewardは正確active turn全文補足accepted・idle恒久pending。同model/effort/cwdを保持。developer本文readbackは非対応、受理と運用品質を混同しない。

最初はownedなし/supervisor idleから自己旧monitor/schedulerを秩序ある停止後にsource更新。再開後の追加report.py編集は手順違反でhash障害を起こし、04:32:52 monitor異常終了・自己owned監督turnを04:32:54にinterruptした。旧失敗/events/turnを保持し正常運用へ書換え0。その後旧identity不在/ownedなし/supervisor idle確認後、同runtimeを安全に復旧。現在scheduler2064203/start16857111、monitor2064518/start16857952、running/reloaded・config/contract loadedと24期待hash不一致0を確認。全期間成功・未来停止・外部NN停止・棋力達成は未認定。

短期自己childは終了、source書込停止。意図的長期2PIDと92停止責任を保持。詳細と再現command: `research-data/ai-sigma/104-session-policy/verification.json`、RPC原応答/期待binding/自己停止: `.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/session-count-104/`。新保存は2MiB目安内、瞬間全host資源保証なし。研究Git版はBeads notesを参照。
