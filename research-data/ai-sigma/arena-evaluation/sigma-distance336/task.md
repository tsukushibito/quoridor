# Sigma対固定D：採択済みthreefold規約での追加比較

Issue `quoridor-4lc.336`。人間が追加比較の実行を承認した。担当は331と同じarena session `01a11062-b120-73a1-8aa3-fe2cb922c7c0`、cwd `/workspaces/quoridor/.worktree/arena-evaluation`。main/Git/indexは324だけが書く。Beadsで331に依存し、331のNNUE対Sigmaの実STOP・回収後に進む。保存セッションへの条件付き依頼は `01a118f1-ec29-7ff1-b173-338119721f9b` で受理済み。待機中に数値時計を予約しない。

保持済みSigma ONNX d790/ORT c902、既存PUCT・K64・tau1・noise offと、固定 `DistanceEvaluator(a0,b8,Tanh)` を比較する。双方のtreeとarenaで同じstandard-2p basic＋補足automatic threefold drawを使う。初期count1、非連続の同一位置への第三到着は合法でdraw、goalを最優先する。位置identityは両pawn・H/V壁・両stock・STM、実historyとsearch pathをroot重複なしで数える。TT/history namespaceも規約に束縛する。200pliesは運用上の収集capで、未終局はUNKNOWN、draw/z0にしない。

同じ保持book93cb、8families・色交換16slots、initial2＋main14を凍結する。100ms whole caller、5ms return reserve、CPU0/thread1/GPU0、ponder/prefetch/engine並行なし。DはTT requested65536/effective4096/1MiB、SigmaはMCTS treeの実費を別に記録する。K停止は実elapsed/workを示し、100ms消費やinference比＝探索/棋力比とはしない。Dのnn_calls0はCPU仕事0ではない。

新規rules/caller/private/source/compiler/main版を凍結し、331の変更のないSigma資格を再用する。Dの変更したlegal/history/terminal/caller境界だけ必要な資格を取る。Torch/native96/旧全suite/book再生成、新教師・fit/export・model/default変更は行わない。334 orderingと335 solverはこの比較に挿入しない。採用版が331比較後に変わる場合は、結果前に別versionを明示する。新規NNUE対Dのtriangle追加対局は今回の承認対象外。

planned16/8pairsを保持し、W/L/true draw/unknown/incomplete、completion rate・unknown bounds、条件付きbook不確実性と共通lineageを報告する。cap/error/cancel/late/no-completedをdraw/forfeitにしない。旧327 RuleA 4W12Lは別rules列の歴史結果であり、新三者cohortや独立反復にしない。Elo・母集団順位・普遍的優位をこの16slotsから主張しない。

当面の支持はSOURCE PLAN ONLY 128KiB。source/config/binding/control/report/関連source確認の全増分を含め、331 source7MiB内の既future contingencyから6750208＋131072＝6881280B（cap7340032B）として保持する。これは追加の対局保存支持ではない。Rootの契約/docs/Git/controlは既Root8MiB内の64KiB。

追加gamesの保守的64MiB見積りは未配分で、最低不足67108864Bに、未価格の必要D資格/private/TMP/audit/recovery/report/review/Git/failureが加わる。331の使用済みoutput・private・旧assets・failed費・UNKNOWNを返金せず、新outputとの同時保持を数える。affected entry前に実whole forecastと支持を固定する。初期source予算はbuild/model/clock/gamesを許可しない。実quiet/fairclock/soleCargo・entry guard成立後だけ開始し、START/STOP/directwait/cleanupを324へ届ける。323pause/seals維持。追加の人間ACKは不要。
