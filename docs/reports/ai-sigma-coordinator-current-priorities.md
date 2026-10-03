# 現在の優先順位と評価・学習計画

2026-10-03版12。ユーザー明示4時間再開08:47:38–12:47:38UTC。新heavy12:37:38、監督12:42:38、monitor12:45:38。親期限の正本と運用は92/stewardが単独所有する。native主評価・高速化効率化を維持する。

主問いは学習データ生成の総費を減らし、独立した学習lineageから全手の教師を既learner/ONNX/少数独立arenaへ接続できるか。Sigma同等は未認定、NNUE型最高棋力は最終目標のまま。前枠173の正式198局95勝103敗、逐次閾値未達で不確かという結論と旧epoch/失敗/期限を保持する。この198局を学習へ転用しない。旧優先計画はGit履歴で保持する。

| 優先 | 問いと到達点 | 費用と判断 |
| --- | --- | --- |
| 主生成・接続176 | 固定Sigma自己対局24局、固定K64で全手π/rootNN/rootmean/z/視点/lineage、game split、CPU小学生/ONNX、条件付き診断4局 | 最終rootだけ配送し毎simulationのCP JSON費を削る。同入力同Kの対応と有効行/job秒を測る。CPU生成900s・学習120s・arena240s・修復240s、計1500s、NN300000。RAM4GiB/guard3.5、3arena CPU2/4/6。GPU結果待ちにせず生成する |
| GPU効率177 | 174 folded推論を私有dynamic batch B1/2/4/8、held stdio APIへ。独立局面各1pendingを束ねる | 同入力数値と転送同期/JSON/IPC込み費用で採否、GPU180s/出力512sample相当、CPU0/RAM2GiB/VRAM6GiB。利益が残る場合だけ176へ最小実生成比較を配分する。元ONNX batch1と区別 |
| 教師品質178 | πと行動、rootNN/rootmean/z、P2合法対応、truncation z未知、lineage split/共通状態漏洩を独立静的裁定 | CPU0/static60s/RAM512MiB。短い物理計算終了を177へ共有。176の全文受入れgateにはしない |

小CPU学習は初期小モデルの機能接続で、fit/速度を棋力としない。本PV構造の大規模訓練・NNUE全面移行・GPU学習・正式NI自動反復は現在配分しない。GPU学習累積2時間の未使用残は不明なので開始せず、CPU接続で前進する。

保存上限12GiBは維持。停止受入れ済173の512MiB予約に対し保存時保守計上244597028Bで未使用292273884B以上を確認、4MiBのみexperimentからhypothesisへprospective再配分する。experiment総予約2044MiB、hypothesis20MiB/guard19MiB。旧保持/未知量減額・削除・親増額なし。176新256MiB/guard224、177新2MiB/guard1.75、178新2MiBはいずれも担当予約内で直前currentを確認する。

CPU4logicalは実job合計。176の3arenaに追加できるCPU重jobは一つ。178短CPU0検算→177 GPU/CPU0実測を順序調整し、自然監督の実jobと競合する場合は次空き窓を選ぶ。RAM配分exp4+hyp2+critic.5+super1+stew.5=8GiB内、実headroomを直前確認する。LLM active数を物理資源gateにしない。

最初の効果確認は176の少数game/適格教師行・総費、177の実batch数値と総route費。主要ボトルネックの改善を実生成へ結び、GPU性能確認だけの連鎖を続けない。条件/探索量を変えた教師は版を分け、量削減だけを質保持利益としない。

92は08:58:38通常freshstart、scheduler3352074/start27085893とmonitor3352088/start27085920、running/loadedと24hash一致を本人報告。親版12SHA0e0e03a157e86bb9d9b7bd0659fb17a3c413afac2286944a5fde839336baae50。初回dispatch競合でownednull、次通常09:18:38。起動の有限成立と未来自然監督/学習成功は分ける。92へ同依頼再配送なし。
