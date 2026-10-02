# quoridor-4lc.92 / 契約4・枠8 起動報告

10:24:22UTC受領、10:32:29UTCに同runtimeをfresh start。旧scheduler2259113/start18105937・monitor2259164/start18106112の同identity不在、state stopped/ownednull、監督notLoadedを確認した。旧最終回収・報告は未受入れ/未確認として別保持し、成功へ変更していない。

親版8 SHA `0f0be04113893b62d3f79ef45bd9d17bd38817622091152d2eb25017acec43fe` とmain/mirror一致。起動前にconfig/contract/prompt、watch、guardの期限と監督運用契約を固定。新絶対期限・硬end拒否・契約延長拒否・設定/構文の6確認を通過。保存supervisor `01a0f6b5-b1bd-7752-b0bb-74a336e459a4` をidle公式resume、設定不変/新turnなし。RPC acceptedと本文読戻し非対応を区別する。

scheduler PID2402552/start19006242、monitor PID2402571/start19006262、boot `ab5e66ac-12ce-49b0-ac55-afe05e3f5216`。実started/state running、24期待hash不一致0、loaded config/contract一致。freshstartでありreloadedイベントは主張しない。周期1200秒/turn180秒/他active数gateなしを維持。監視開始後source編集なし。115には触れていない。

10:33時点の新run約96KiB、限定steward保持11,169,792B、既予約128MiB/combinedguard112MiB内、追加予約0。scheduler RSS76,124,160B＋monitor20,721,664B、affinity[0]。標本current RSSと過去peakを分け、全体12GiBを再測定したとはしない。短期自己identity不在/childなし/exit0を本文前保存。意図的長期2PIDは維持する。

92本人ownerとして14:05:49新重job停止通知、14:10:49正確ownedturn＋scheduler停止、14:13:49monitor回収、14:15:49必要証拠保存を保持。起動受入れと未来wholeturn/最終停止/外部NN停止を分け、92はin_progressのまま引渡す。

詳細: `research-data/ai-sigma/92-frame8/manifest.json`、`.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame8/{before-start,source-changes,validation-cases,supervisor-resume,live-applied,current-resource,short-stop}.json`。旧bytesは既Git/run参照、全履歴コピーなし。
