# finish全経路25秒の静的点検

旧 `d3edcbd1` のfinishは3show全exit0/directchildwait済み、同self stdout SHA/525,281Bを二度読んだ後に外側25秒で停止。notes append/backup未実施、別backup exit0という原差を保持する。先の自然run5wrapper成功と、per-command回収改善の支持も変更しない。元runは読取のみ、判断品質・科学成果をこの故障へ代弁させない。

## 上界と観測

現sourceは共通goal/self認証2show後、finishでselfを再showし、append/backupする5wrapper。各wrapperにper-command25秒があり、回収は最大3+3秒。単純source上界は155秒にfilesystem/RPC/guard費を足す形で、全経路25秒を証明できない。初回+5wrapperでadmit6回、24inputを各確認する144hash読取、keeper/Supervisor各rootwalk計12回がある。保存receiptの局所容量確認も別に必要。hard operation end、ownership/pause、per-command資源確認を省いて速くする案は採らない。原ログはcommand完了時刻を持つが、admit/DB/serializationの個別elapsedはなく、支配費の確定はUNKNOWN。

現wrapper公式`show --help`の`--brief-deps`と複数IDを利用し、一回のshowでgoal/selfを現在読取できた。実小readonly commandは `bounded-wrapper-proof.json`。stdout526,824B/1.570742秒で、status/labels/assigneeを保持しdependencyはidentityだけ。これは一回の静的診断で、未来time保証ではない。raw/full notesは保存しない。

## 必要修正案

1. finishは短notesの1024byte cap検査を読取前に済ませ、goal/selfを一回の `show goal self --json --brief-deps` で認証する。返却ID集合・件数・owner/status/pauseを検査し、そのselfを同finishだけで再利用する。別run/古いobserved状態を認証へ流用しない。appendは既conditional-assignee/statusを維持、backupはappend完了後。3wrapperへ減らし、同self再showを除く。共通observe/inspectも必要範囲のbatched認証へ移せるが、無関係な全役/全履歴を読まない。依存の詳細が判断に必要なら既bounded inspectへ。
2. 3wrapperでも25秒/commandの和は93秒＋周辺費であり、全finish25秒の証明にはならない。既outer25秒と同じ累積残量から各stageのtimeout/回収・記録余裕を派生させる必要がある。ownedturn/null/end時計は新しく取り直さず、cap追加やtimeout増加をしない。単にcaptureごとに25秒をresetしない。admit/保存費もこの残量へ含める。正常finishを25以内に収める具体stage費は現在ログから未確定で、実測の上界が成立するまではtyped不足を保持する。soft timeout後の安全回収が25秒外へ出る可能性と、hard kill/IO障害の欠測を区別する。
3. phase別の開始/終了・費を既小receiptに足し、開始前の不足はspawn0、停止点のnotes/backup到達を個別記録する。append応答不明では全finishを再試行せず、元receipt/通常履歴で確認する。保存済commandのstdout実bytes/SHAと欠測を維持する。外側期限のためbackupが未実施なら別既backup経路の費/receiptを残し、wholefinish成功へ付け替えない。

## 担当・費・次の機会

owner92、scopeはmain watch/既canonical tests/必要expectationsだけ。prospective案だけで本turnのlive source/24hash/runtime/promptは不変更。実装前にexact science readersの自然停止、Supervisor公式idle/ownednullを確認する通常安全窓で扱う。science中やactive Supへのinterruptはしない。窓が成立しない待ちは科学の新gateにせず、未適用pendingを返す。

設計・prospective差分と必要mockは管理作業10–20分目安、既CPU0 single/RAM1GiB内、checkerは60CPU秒以下、差分/小証拠/uniqueGit forecast256KiB以内を既112MiB/current+remainingから事前admitする案。新予約ではない。実適用は既own2 stop→source固定/必要24hash→validate→通常start/load/exact2の費を含め5分以内目安で、実remainingを直前確認。新依存/helper/layer/強制tickは不要。必要mockはbatched malformedID/pause/owner/conditional update・累積不足時spawn0・append応答不明・backup未到達/receipt/回収を検査し、既14watch testsを再用。科学/NN/build/GPUを起動しない。

batchだけの修復を全finish保証と呼ばず、次自然runのphase費/notes/backupと失敗点で採否を更新する。終了23:26/31/34/36:03、Coordinator恒久idle refreshの別pending、92 in_progressは維持する。
