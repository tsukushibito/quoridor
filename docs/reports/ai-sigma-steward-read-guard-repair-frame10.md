# frame10 監督read guard会計修復 / quoridor-4lc.92

契約8補足に基づく現在修復。受領・実開始2026-10-03 02:36:09 UTC。旧7件の点検失敗と、公式turn completedでもobserve/notes/backupが未成立だった事実を保持する。

原因は監督の全期間出力104,181,760Bをstewardの112MiB guardに合算する所有範囲の不一致。旧式合計118,251,520B、inode重複0。監督のframe10 binding付き保持量は143,360Bだった。既watchと同じsteward所有範囲16,723,968Bと、監督の現frame保持を分け、既steward128MiB予約/112MiB guard、監督32MiB予約内で各command前に4MiB forecastを照合する。重複inodeを一度だけ計上し、現在の未知所有・読取不能は拒否する。過去保持量と旧unknownは親保守会計に残す。削除・容量移管・上限増加・親減額は行っていない。共有Git帰属や全親現在量の再認定はしていない。

小mock6件で重複/実超過/予約内/unknown/期限/pauseを確認。超過・期限・pauseではspawn0を保持し、必要3sourceの構文とvalidateが通った。旧ownednullと監督idleを公式確認し、正確な旧2identityを秩序停止してからsource/期待bindingを固定。公式idle resumeは同設定で受理、developer本文readbackは非対応。同runtimeを通常fresh startした（reloadedではない）。02:44:25現在scheduler3070572/start24839468、monitor3070586/start24839490がrunning、24期待hashとloaded config/contract一致。次通常02:53:22を維持、位相差約−0.062秒。sourceは再開前に固定し、再開後追編集なし。

適用source Git b86f9530299e27686927fcfef53d6c4b4abb1c5f。必要な元rawは参照とhashを保持し、全履歴コピーはしない。詳細は[修復manifest](../../research-data/ai-sigma/92-frame10-guard-repair/manifest.json)と作業領域`.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame10-guard-repair/`。

通常run8407c748 / exact turn01a0ffaeでobserveと追加inspectが成立し、15commandすべてexit0/reaped。notes追記・backup各exit0、self-stop02:55:01、公式turn completed/errornullとidle、scheduler owned解除を02:56:34に確認した。notification.jsonにも統括通知の受理を保存。これは今回通常点検の有限復旧確認であり、旧7失敗・全期間遵守・瞬間peak・未来点検成功・外部NN停止・研究改善の保証へ格上げしない。詳細natural-effect.json参照。

92はin_progressを維持。04:05:21新重job開始停止通知、04:10:21正確ownedturn+scheduler停止、04:13:21同identity monitor回収、04:15:21証拠保存の同owner責任を保持する。155/156 source・データ・研究条件へ変更0。外部NN全停止や棋力改善は認定しない。
