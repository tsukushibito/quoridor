# 枠10 研究実配分・起動引渡し
現候補Q0/C1.5と固定Sigmaの棋力差を新しい層化局面で測ることを主研究へ変更した。145 Cmatchedを自動実行せず、旧119の4勝12敗を候補不足の前提にしない。147critic/148hypothesisの独立速報を採用し、32prefix（4/5/12/13ply各8）×色交換64game、hash混合seed、巡回層/交互色順、全未知score分母と探索的精度を結果前に固定して149へ実配送した。9bafd9ef / docs/design/ai-sigma-frame10-gap-preregister-supplement.md を参照。最初game前のpreregister/source/input固定は149担当。今回の調整は入力生成seedの連番由来偏りを避けるもので、均衡/IID/一般実戦を保証しない。

本人開始は92 00:27:48.859040、147受領00:27:40/claim00:28:06、148 00:28:22.929797、149 00:28:04.562204UTC。既saved同設定への配送と本人claim/静的開始を区別して保存した。旧hypothesis systemErrorに対する今回一度の新turnはユーザー明示再開によるもの。旧usageLimit失敗は保持し、盲目再送/モデル変更/daemon restartなし。科学game完了はこの起動記録時点で未確認。

92steward単独ownerによるfresh start/loaded config-contract/24期待hash一致を有限受入れ。00:36:39UTCにscheduler2947990/start24053182・monitor2948006/start24053214の現在同identity、state running/recoveryfalse、実config/contract hashとloaded一致を統括でも確認した。root146独立受入れは /workspaces/quoridor/.artifacts/research-team/resume-20261003-001521/root-acceptance.json。本人短期source書込停止・backup/引渡しを受領し92は長期責任のためin_progress維持。旧frame9最終受入れ/旧frame8不足を別保持し、外部NN停止・未来4時間成功・本文判断品質を認定しない。

147/148は最終静的結果をcoordinatorへ、149は入力固定/実pair/停止をcoordinatorへ報告する。実験準備開始と運用受入れを研究成果に置換せず、次のpair集計で差/量交絡/尺度感度を評価し配分を変える。監督の独立節目評価を通常運用で受け、採否と実配分/効果確認を返す。root146/92事務完了や全role最終本文は研究の新gateではない。

親4CPU/RAM8GiB/保持＋有効未使用予約12GiBを維持し新親予約なし。統括の本起動記録はCPU0短期管理/軽いJSON照合のみ、新NN/Chrome/build/game0、保存約数十KiB＋既Git参照（Git全増分のowner帰属は未集計）。原成果/defaultindex/共有source編集0、専用indexの正確自域だけ保存。短管理commandの全期間PID/RSS/瞬間peakは未記録。04:05:21新heavy停止/04:10:21監督/04:13:21monitor/04:15:21全終了UTCを92同ownerが保持。Sigma同等/正式NI未達、次枠自動実行0。

証拠: research-data/ai-sigma/frame10-coordinator-start/{allocation-and-start,intake-current,runtime-current-check,adopted-seeds}.json。
