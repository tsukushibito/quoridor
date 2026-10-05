# 92 有界監督記録の現在修復

受領・実開始05:38:33 UTC、親11と長期08:05:21/08:10:21/08:13:21/08:15:21を維持。原因は現在保持29,708,288Bが既32MiB内でも、旧4MiB forecastとの合計で拒否されること。前標本を現在値へ置換せず、旧104,038,400B履歴と既raw・失敗を保持し、削除・圧縮救済・移管・予約増・親減額はしていない。

新runのみwrapperをpipe一時メモリで読み（4MiB cap）、status/owner/labels/依存参照/更新時刻/現在本文とnotesのbyte区間を選択保存する。元size/SHA・不足・元command/exitを保存し、同selectionは内容参照で再利用。既beads.shを使いDB直読み0。description通常3072byte/notes最新1024byte、必要不足はfield/offset inspectで最大8192byte区間を追加確認できる。欠測をpassにせず、科学raw/重要失敗/予定分母は変更しない。

実capはcommand24（finish/backup込み）、selection64KiB、guardrun384KiB（失敗余裕8KiB）、notes追記UTF8 1024byte、独立判断handoff16KiB。forecast512KiBはrun cap＋一時write64KiB＋失敗/短報告/dir余裕から設定。guardは書込・次spawn前に実allocatedを確認し、既watchは新policy runだけ合計512KiBを標本監視する。全host瞬間peakやguard外書込の完全保証とは区別。現在の32MiB/親12GiBは不変。

11小確認通過（pipe実超過・子回収、nextspawn0、unknown/期限/pause、UTF8範囲、dedup、notes cap、構文）。保存済みcore556943B→selection5952B、元rawhash不変。05:53自然run0bd85f42/turn01a10052はobserve成立、12commandの読取/selection成立、保持221184B・旧巨大全stdout保存0。ただしfinish05:56:09は残9秒/必要36秒の期限拒否、notes/backup/self-stop未成立、scheduler turn_limitと公式completed/errornullを別々に保持。完全復旧は未成立。

正確ownedなし/公式idleで再び秩序停止し、短いfinishを全判断整理より先に保存するprompt/運用本文へ最小修正した。90秒は保存の目安で読取禁止を追加せず、180秒時計を延長しない。独立判断は残時間の短報告に保持する。全source固定→validate→同runtime通常freshstart、24期待hash/loaded一致、same supervisor idle resume同settings受理/readback非対応。次通常06:13:15の効果は未確認で引渡し、manualtick/新turn0。現在identityと必要根拠は作業領域bounded-records/final-live.json等を参照。

自短期source書込停止、既92 in_progress/未来停止責任を保持。研究165169 source/data/モデルと親/common/role/registry/mainは変更0。反映成功を自然監督全期間成功・研究の改善・外部NN停止へ格上げしない。

統括の独立4JSON読取は新run論理filebytes約150144Bを確認、本人のallocated221184Bと別指標として保持する。後着採択f61080aは今回finish先行対応を採用し追加source変更/stop-start/時計resetを要求しない。既適用へ統合し、次通常06:13頃のobserve/finish/notes/backupと保存実増分を同92運用で効果確認する。長期停止責任を維持する。
