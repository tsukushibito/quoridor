# 容量観測タイムアウトの修復

Root issue quoridor-4lc.322。ユーザーが作業基盤の修復を最優先に指定し、容量判定に必要な範囲だけを修正した。学習・探索・モデル・データ・予算の数学は変更していない。

mainはホスト共有9p、worktreeはext4。旧observerはPath.lstatを直列に実行し、重なるrootを再stat/scandirしていた。診断ではmainの研究記録を約7,000path確認するだけで約21秒。旧学習12/35秒とRoot120秒のtimeoutは未完了のまま保持。

修復はDirEntryのmetadataを使う8本のbounded I/Oと、一回のobserve内だけのmetadata/子一覧再用。ThreadPoolへの投入は128件ずつ。root順のdev/inode配分、hardlink重複排除、root別exclude、symlink非追跡、予約のunused、UNKNOWN128MiB、12GiB上限とmissing/race時のunknown拒否を維持。永続cacheは作らず、次のobserveはfresh。root単位のprogressは診断時だけ任意出力。

同じrecipient全manifest＋canonical search evidence rootを観測し、29.861秒・exit0/direct child waitで完成。current＋unused＋UNKNOWN＝12,873,568,256B < cap12,884,901,888B、余裕11,333,632B、errors0。97709 metadata queries、child peakRSS156948KiB。観測時点の容量判定であり、atomic snapshotや将来の全期間保証ではない。圧縮結果と復元SHAはverification.jsonへ束縛。

4個の限定testで重複root/hardlink/exclude/symlink/次観測の変更反映/race/unknown/over判定を確認。旧版との静止fixture比較は時刻以外の既存fieldsが全一致。Ruff/format/diffcheck PASS。全史監査やモデルforward、build、GPUは修復中0。

完成結果を学習の既存sessionへ直接配送accepted。初回blocked拒否はRPC前で保存し、capacity-only blockerを結果成立後にCAS解消した。同じ対象・予約に対して担当ごとに全体を再走査しない。学習NEW120の旧supportupper52.036105458は保持し、残upper67.963894542内でONE native phaseの上限を下げる指示のみ。旧600/300 UNKNOWN、Root旧timeout費、全failed receiptはrefund/成功付替え0。新モデル/fit/sealedtest release0。native数値検証・科学結論はこの修復と別。
