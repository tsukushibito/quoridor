# frame21 NNUE最高棋力へ：期待される学習利益が棋力に現れない原因と設計改善
ユーザー明示2h 2026-10-05 08:37:54–10:37:54UTC、重job入口10:27:54/監督正owned10:32:54/monitor10:35:54/保存10:37:54固定。親継続・旧期限/結果/失敗/UNKNOWN/累積不変更。現行文書 docs/design/ai-sigma-continuation-20261001.md の版21・運用binding更新は92 solewriterへ一度実配送済み、staticは稼働待ちgate0/heavyは各ownerfreshactualadmit。

主問いは利益有無の採否でなく、距離以上に強いNNUEを作るための原因と改善。現QF1は二視点312疎入力＋distance2で全距離map入力ではない。Sigma/Claustrophobia固定一次sourceから有効経路/壁/移動情報を疎特徴・差分更新・低費用後段へ落とし込む265選定と、意味ある228凍結L/忠実I/現距離Dを同Rust条件で結ぶ266を実配分。具体案決定時に選んだ特徴/教師/学習・理由/代替・担当/最初の測定をroot/ユーザーへ通知、全稿ACKなし。

探索高速化も独立実作業を並行配分。αβとMCTS教師生成の支配費を分け、共通coreの1介入を同仕事/同品質/同Kから有効教師行/全job秒・同時間depthへ結び、特徴追加費とのtradeoffを選定へ返す。高速化の担当/開始は別子issueでBeads正本、全分析完了待ち0。

評価主層は拮抗多様opening/色交換、偏った即勝/浅強制等は別能力層、Sigma閾値だけ必須gate0。訓練は優劣/拮抗/終盤の構成比/重複/有効量を管理して評価選定と区別。旧2prefixと機能10step0W4Lは一般強弱/NNUE限界を判定しない。教師情報/探索量/分布、特徴情報/尺度、学習fit-generalization、value/terminal/delta/leaf接続、費/depthを競合原因として観測で順位更新。未見学習利益/SigmaNI/最高棋力未達、229final算術NOT_RUN・173正式198非学習/開封test非選定維持。

main Rust/Pythonが正本、旧WTはモデル入力保護、廃止Node復活0。CPU計算合計4logical/RAMcurrent8GiB/保持+有效unused12GiB、GPU推論6GiB/30min、GPU学習旧確認unusedのみ（未知なら新0）、native現物余裕も守る。資産/依存/環境更新/製品統合push公開/未知削除0。各担当Beads scope/resource/終了と自己子回収、singleGit統合coordinator、92運用solo。92に枠内終了点検/整理長期保守判断と長期停止を実委任、Supervisorは既自然点検で選定/異論採否/費/効果と自身干渉を評価。研究結果ごとに現在優先度と保留再検討条件を更新、全役承認・ACK起床・自動延長0。
