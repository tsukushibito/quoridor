# 初期LR0.01・減衰patience1の結果と一時停止

同じINITIAL、全original T/V、batch2048、反転RNG、減衰倍率0.5で、減衰patienceだけ2から1へ変更した。epoch0–15の全V MSEは完全一致した。

| 条件 | 最初の減衰 | 完了epoch | strict BEST全V MSE | controller全時間 |
| --- | ---: | ---: | ---: | ---: |
| 以前: patience2 | 19 | 62 | 0.4275190322058281 | 2362.165468170秒 |
| 今回: patience1 | 15 | 51 | 0.42744088098494515 | 1751.2053312249482秒 |

同程度の観測MSEを保ち、成功optimizer更新と元観測seenは17.74%減少した。実時間は39分22秒から29分11秒へ短縮したが、以前のrunにはCriterionの純compile同時実行があり、25.86%というwall差を公平な因果速度比とはしない。今回epoch区間中央値は32.04秒（評価・保存を含む）。

全V MSEの初回到達は0.435が20→16epoch、0.43が32→28epoch。今回の51epochは209559更新・429111399元観測seen。BEST=LAST51、最後の有意改善reset43からstale8で科学的停止。43→51の微小改善は0.0000479886。BESTの実更新LRは1.953125e-5で、停止時selector後に記録された9.765625e-6では更新していない。

事前の厳しいnear-reference目標0.42605264436242674は両条件とも未達。全既存候補中の最小MSEはinitialLR0.011321930132219958の0.42505264436242673で、その記録を変更しない。今回のユーザー指示は最小値更新より同精度帯と時間短縮を優先し、一旦ここまでとするもの。事前目標を後から達成扱いにせず、追加fit・factor0.25・native数値資格・Sigma/newE開封を停止する。

INITIAL/BEST/LASTのPT metadata・有限Adam・native保存パラメータbyte、全T row各51visit・V optimizer visit0、freeze参照SHA、18source SHA、private ELF/library/config/cache/T-scale/constant bindingを確認。実trained native推論一致は未実行。最終cohort freezeとnewE/Sigmaは未開封・保留。原失敗・費・UNKNOWN・全資産を保持する。

Job8b672b9d START2026-10-07T02:06:21.570211Z、自然STOP02:35:31.861342Z。controller/trainer exit0、direct child reaped、cleanup_complete=true、remaining=[]、記録guardian/trainer PID/startは不存在。比較PNGは保存済み全V記録のみから生成・目視確認済み。source writer停止、main/Git操作0、現在/次learner numerical予約なし。

実証拠: trigger-patience1-stop-collection-v1.json、trigger-patience1-stop-receipt-v1.json。比較画像: /workspaces/quoridor/.worktree/assets/checkpoints/public-full-learning/trigger-patience-v1/patience1/comparison-v1/comparison.png。
