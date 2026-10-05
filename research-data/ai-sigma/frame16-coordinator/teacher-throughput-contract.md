# 教師生成の品質維持効率化 / frame16延長17

問い: 大規模な独立局数増量の前に、成立済みGPU24active/maxB8/held provider多handle生成の支配費を実測し、教師品質・探索量・多様性を保つ薄い実装で、有効Rjoint/全attempt jobwallと予定増量費を改善できるか。
選定理由: 現96trainは小診断規模でデータ不足を除外できない。fit/gap分析は必要境界まで保存済み。追加小診断やfresh testより、今後の桁違い局数検証を実用にする生成効率をユーザーが優先した。B/active増だけを決め打ちせずqueue/IPC/encoding/記録/初期化/尾部を競合案として短く比較する。

所有: 既saved experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746。cwd /workspaces/quoridor/.worktree/ai-sigma。solewrite tools/ai-sigma-teacher-throughput/、research-data/ai-sigma/frame16-teacher-throughput/、docs/reports/ai-sigma-experiment-teacher-throughput.md。旧187/194/201/205のsource/model/export/checkerは停止SHA readonly参照。shared/source/環境/モデル/role/push変更なし。

216有限受入れ根拠: research-data/ai-sigma/frame16-coordinator/216-final-generation-boundary-acceptance.json。phase1/2/4の独立支持、phase3/5 owner-only、phase6未開始停止を区別して受入れ。本人216close+backup後、新issue ready/show/no pause/claimし、この実質新課題を開始。専用close turn不要。新運用の全史検査/全役承認/root再確認を静的開始gateにしない。

実施: まず既保存broker/provider/worker費とsourceを短く読み、baseline現在GPU24/B8を比較正本にする。主な支配費・最小変更・有力競合案・比較する条件/登録game数/quality/numeric確認を結果前に自域preregisterへ具体化して統括へ返す。その後は本配分内で実装・測定へ進み、再承認待ちにしない。独立criticの提案は到着時反映/理由を残す。最大2主条件(現baselineと1改善方式)、必要なら同条件確認1jobまでを一課題にまとめる。最大3生成job、各登録96game以下/active48以下/actualB32以下を上界とするが、上界の実行を義務にしない。既B8を超えるものはprivate provider/broker薄変更でpartial/full ID対応/f32 finite parity/RAM/VRAMを先に確認、既B8認証と混同しない。条件差を増やす時は輸送・queue主変更と資源差を区別する。巨大基盤/言語移植/RuleA再移植は先行しない。

品質: 同model d790/同K64/root64edge63/tau/RuleA特徴history合法Action P2mapping/pi/z/独立opening family多様性を維持。baseline/candidateは同固定opening manifest/seed/仕事量で比較することを第一候補とし、numeric差で経路が変わる可能性、hostwarm/管理CPU/尾部等の交絡を保存。条件内重複兄弟行やK削減を品質維持速度へ読み替えない。全予定/全attempt fault/censoring/NOT_STARTED/0eligibleを分母保持し、success補充しない。共有既資格算術を新rawへ有限実施、先生真値/棋力認定なし。benchmark生成物は訓練へ自動混合しない。旧test label/result/173正式教師への選定読取・転用なし。

測定: 全attempt guardian jobwall(coldinit/終了回収込み)と有効Rpolicy/Rz/Rjoint、game秒、actual batch分布、queue待ち/IPC/encoding/記録/provider/初期化/尾部の測定可能な費、logicalNN/startup/discard、current/peak RSS/VRAM/CPU数を保存。重なったphaseの単純和を全wallと呼ばない。現在CPUJS/GPU24のどれとの比較か明示しRustCPU unknownを救済しない。品質成立/接続成功/速度/学習価値/棋力を区別する。

予算: CPU最大4論理(番号ではなく同時計算数)、例worker2/4/6各1+provider0単1、torch/BLAS/ORT threads1。GPU推論6GiB/job最大600s(親30分以下)、新学習0。各science直前goal+self ownership/pause/exactPIDtick/currentRSS/unknown heavy/GPUcurrent/正live monitor owned/quiet>=hard+30sをfreshadmitし、CPU0自然監督と合計上限を超えない。RAMこのjob6GiB/guard5.5GiB、研究全体8GiB current確認。GPUjob開始前の数値確認も同所有guard、parity未成立ならcandidate開始0として保存。累積heavy1800s以内、全NN equivalent900000以内(数値確認/startup/失敗含む)、静的source/math180s以内、管理保存600s以内。各必要job source/command/actualstart/identity/wall/peak/exit/全childwait/currentexactabsentを保存し、所有不明/guard/pause/期限なら停止。

保存: 新subreserve128MiBを既experiment effective1980MiB内の確認済みunusedへ計上、scopeguard112MiB incl必要Git/temp/cache/receipt。旧21616MiBその他未知保持は減額しない、親12GiB追加0。旧ledger unused1313972224Bの後続割当も確認し、新actual+forecast+未使用予約をscience直前算定、不足なら量縮小又はtyped未開始。数値/資格に必要なmember/source/outputを小pack/Git byte復元しindex不変、backup sync。全raw追加コピー/新モデルなし。

期限: 明示連続延長の開始05:55:50維持/親終了09:55:50 UTC。本課題newheavy09:25:50、science全停止09:35:50、必要保存09:45:50、submit09:50:50まで。親newheavy09:45:50/監督09:50:50/monitor09:53:50/最終09:55:50は92。旧個別run期限は変えない。

次判断: 倍率の固定gateや無限最適化ではなく、見込100/1000/10000独立game規模(単なる費用シナリオ、今実生成許可数ではない)の時間/保持量、今回の準備+検証総費の回収局数を見積もり、改善継続/打切り/将来増量を選ぶ。今回短測定の追加条件は情報と回収費で判断。『速い』だけをgoal達成としない。新規模生成は本benchmark上界外へ自動開始しない。
