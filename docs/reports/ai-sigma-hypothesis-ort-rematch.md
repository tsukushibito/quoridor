# SIGMA-ORT-REMATCH-PLAN / quoridor-4lc.32
hypothesis → coordinator。受入れ待ち、実実行no-go。
契約全文・SHA f13d0b2d…601fc5c確認。旧.21/.30原文copy・差分・hash保存、旧入力23実hash不変。固定model/Wasm/fixture/.30manifestの指定hash照合。
未使用56からseed2026100204で10prefix [10,6,45,39,42,43,33,12,32,27] を固定。seed2026100205順 [32,12,39,10,6,42,43,33,27,45]、色順はpreregister.json。browserのみ20局/m10/T500g91/探索seed1979、retry pair1/global2、責任・Xi・参考L・分類を勝敗前固定。pool64合法履歴/残ply/重複/golden除外再検査、training overlap未確認。旧32局と統合しない。
.21入口を20browser/10pairに変更、.30 ORT arenaへ接続。参照実入力prefix/ID/gen/engine/seed/limitsをproducer echo、両caller照合。mockのforeign-prefix合法action拒否、20採番/色/seed/score、retry1/global2/枯渇、責任分類、pause/deadline/signal、無応答即discard・cleanup hangを確認。取消直後null backendの初回失敗を保持し、結果採用前guard修正1回、revision2成功。新token正経路/既run実入口・signalCode実child・bounded browser cleanupは未完了。manifest entry_mock_complete=falseで実--run fail-closed。
NN/browser/binary/build/対局/実holdout送信/委譲0。旧negative・39配送stamp・goal未達/正式NI未立証を保持。独立.31＋統括freezeまで禁止、同期限03:55に2760秒+reserve不足ならno-go。競合A/B/C・時計/探索/小標本を維持、棋力認定0。
詳細: .artifacts/ai-sigma/plans/SIGMA-ORT-REMATCH/{preregister.json,mock-summary.json,adapter.patch,entry-final-manifest.json,writer-stopped.json}。source書込停止、自己mock PID0/exit確認、瞬間peak保証なし。資源詳細writer-stopped/process JSON、copy/読取・終了整理のRSS/CPUは欠測。状態正本Beads、自.32 in_progress。後続は統括へ不足gateを返す。採用と通信acceptedを区別。
