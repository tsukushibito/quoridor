# quoridor-4lc.92 / 契約5 詳細選択改善

11:57:17UTC受領。原因はselect_currentが担当付きin_progressをreadyより先にしたこと。現在運用92とreadyを優先し、その他は更新日時順へ最小変更。goal/selfは従来coreで取得、8詳細枠とdirect24/nested3×8の上限を維持。状態・依存参照・本文・pause/所有・namespace/期限の意味は変えない。119専用条件なし。

監督0abce05bの保存current raw191,182B SHA `5558ae6db210a6e1c4c89e57d62b241a0f5e9cb1f0895b3564234dea3ab22531` は不変。旧選択92/38/75/74/73/72/71/70から新92/119/38/75/74/73/72/71へ。未来ready/最近の担当/blocked・依存・重複・pause/未知自己ownerと拒否条件不変の7確認pass。rawの参照を保存し全コピーは増やさない。

監督completed/idle・ownedなしを正規App Serverで確認し、dispatch lock内の正確自己monitor SIGTERMで秩序停止。旧2identity不在/ownednullを確認後guardとconfig.start_atを固定。fresh start実started/state running、scheduler2477008/start19538464・monitor2478518/start19545447、boot ab5e66ac-12ce-49b0-ac55-afe05e3f5216。24期待hash/loaded config-contract一致、変更期待hashはguardとconfigのみ。reloadedイベントは主張しない。

実running gap 144.262707秒。保存next_atをstart_atで維持し12:12:29UTC予定、差-0.001590490秒。初期runningのnext_at nullで確認処理が例外となった証拠を保持、二重startせず初期化後を確認した。監視開始後source追加編集なし。119研究・role/registry/parent/周期1200/turn180/停止期限は変更0。

新scope 86016B、限定steward保持11931648B、追加予約0・既128MiB/combined112MiB内。現在RSS合算52506624B、CPU affinity[0]。過去peakと現在量は分け、全体12GiB再測定とはしない。短期identity不在/childなし/exit0とsource停止を本文前保存。長期2PIDは92owner責任として残す。

次自然snapshotで119等の詳細入り・補完inspect回数/出力量の効果はsupervisorが追跡、現在未観測。起動確認をwholeturn成功・棋力改善へ格上げしない。14:05:49通知/14:10:49正確owned+scheduler停止/14:13:49monitor回収/14:15:49保存責任を維持、旧枠7最終報告未受入れも別保持。

根拠: `.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame8-selection/` のraw-reference、selection-validation、orderly-stop、live-applied、current-resource、short-stop。再現: raw-referenceの保存current stdoutをselect_currentへready119付きで入力（新8選択はselection-validationに記録）。validate command: `python -B .artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/scheduler.py validate --config .artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json`。稼働中のstart重複は禁止。
