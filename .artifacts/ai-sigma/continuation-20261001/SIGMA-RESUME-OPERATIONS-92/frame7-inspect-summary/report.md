# 92 frame7 inspect依存summary改善

監督f08d35f3のinspect110の提案を採用し、07:55:29UTCに受領/開始。guardのinspect返却だけ、各issueのdependenciesへ既dependency_summaryを適用。issue_summary全体は転用せず、id/title/status/owner/description/acceptance_criteria/notes等のその他本文は全て維持。wrapper raw・元stdout/保存inspect/Gitは変更0。

少数fixtureと保存raw1件の5確認＋構文pass。依存ID/type/status/assignee/labels・選択issue110と必要本文/notesを維持。返却bytes120540→3418（約97.2%削減）、原raw119732B/SHA4e8b273686dba4363d0ca76a29d63795c45fa2d6fad718b49e449bf84d246bff不変。30136tokens/truncateは監督報告値で再tokenizeしていない。selected pause/未知core owner/namespace拒否も確認。硬い期限/自己child回収/observeの意味変更0。110性能測定source/dataは編集・停止0。

監督自然終了/idle・ownedなし・正確identityを確認し、旧monitor/schedulerを秩序停止→guard最小差分/必要binding固定→validate→同runtime fresh restartでrunning・実loaded config/contractを確認。新scheduler2259113/start18105937、monitor2259164/start18106112、24期待hash不一致0。旧gap/失敗履歴を保持し成功へ書換え0。

次回08:07:16UTCを維持するためconfig start_atへ保存した次予定を設定（差約5.5μs）。通常SIGHUP reloadは次回をnow+1200へ動かすため今回は行わず、fresh startの実loaded/startedを証拠とする。reloadedイベントが出たという主張はしない。周期1200/turn180/他active数gate無し・10:02:31重job通知/10:07:31監督/10:10:31回収/10:12:31全終了は不変。監視開始後のsource追加編集0。

短期child/source書込停止、意図的長期2PIDと92長期責任を保持。次自然点検のinspect返却量・読取負担/notes/self-stopを40/92で追う、今回のfixture/loadedを未来whole-turnや棋力改善へ格上げ0。新2MiB目安/既128MiB内追加予約0、瞬間全host peak保証なし。

検証/差分/実command/actual gap/自己停止/Git: 同frame7-inspect-summaryディレクトリのverification.json/source-changes.json/commands.json/live-applied.json/self-stop.json/git.json。原採用根拠のsaved raw参照もverification.jsonに記録。
