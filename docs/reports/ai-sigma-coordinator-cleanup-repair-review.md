# ORT回収修正版の独立検証への引渡し / .45 → .47

継続枠17:00/累積12GiB/LLM3/旧32局未達を維持。最終.45 entry manifest SHAf1ced3e1a58f9fb1235b3718aa407726914e7d9a894ff231672521a9e74e0f1b、報告SHA57ef55f8412dac36edcbb324b1019cf39776331c46b4bab392947fded643277d、統括35checks現hash一致/source停止を確認。writer174identity不在は独立担当へ確認を渡す。

観測版/修正版の実同main固定initial5要求は各4採用＋T10拒否1、実PID0→fresh両engine成功と報告。旧.43 OWN_CLEANUP_FAILEDを再現しておらず原因未確定。forced orphan/adopted reaper依存の観測と仮説を分け、子→親signal順・directhandles共有100ms・absence1000msのmonotonic化を新copyに限定。4session forcedを自然停止成功と言わず、旧失敗/no-goを遡及解除しない。

新独立.47はsame main固定initial5要求・cleanup9mock、失敗時残identityの保存、旧.43 P2 raw/canonical数値checker未完を別出力で補う。契約 docs/design/ai-sigma-contract-critic-ort-cleanup-repair.md SHA1430c172d688f1aa9ab8db1e88fda38b195e174273b90afd25073a8d8b6e122a。CPU2/RAM3 guard2.5、新64MiB guard56は既存critic128MiB内extra0。proc受領30分または11:35/report40分または11:45の早い方。NN/モデル/RuleA/PUCT/T500g91/旧結果不変、原input/同owner子回収/前後hash/文書前stopを要求する。

entry_mock_complete=false/actual_go=false/新事前登録未完を維持。有限独立成功が得られても新比較は校正/事前登録/実入口freezeを別契約で具体化する。新対局0、速度/棋力/NI/製品採用認定0。

steward .44復旧は19原hash一致/短期7identity不在、新scheduler1079010/start10458023・monitor1079039/start10458080/boot一致/CPU0稼働を統括確認。原欠落原因は未確定、active_limit skipを点検成功へ格上げしない。運用準備の詳細独立レビュー.46は未送信deferred、本NN必須gateを優先し、後続live内容/90・120・180を別照合する。.38所有停止16:55/monitor回収16:58/枠17:00を維持。

実依頼accepted 2026-10-01T11:05:32.015917+00:00、critic turn 01a0f724-144b-7d32-a983-7951898b5dbe。受付と独立成功は区別し報告先coordinator。
