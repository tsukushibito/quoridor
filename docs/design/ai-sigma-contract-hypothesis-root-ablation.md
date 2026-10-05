# 固定根統計での選択規則の一要因診断

quoridor-4lc.28 / SIGMA-ROOT-SELECTION-ABLATION / 試行1 / 版1。hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。目標契約ai-sigma-research-goal.md版2全文、AGENTS/common/role/team/design/storage/handoff/protocolを継承、global04:00UTC/JST13:00。過去逸脱遡及適合0、通常製品/主checkout/他worktree/M2/UI/描画/.26/source/rootlockへのwrite0、追加委譲/GPU/学習/取得/NN/全MCTS/追加対局0。

問いは同じ最終根統計を固定した1回のselect/finishで、どの規則差がargmaxを変えるか。backend案A/B/CとH1〜H4を保持。これは反実仮想一歩だけの有限機能診断で、変更後の木・NN・visits・棋力を推定する実験ではない。採用/正式NI/goal認定0。

入力は.27read-only request-records.json、analysis.json、matched-records.json、frozen kernel .artifacts/ai-sigma/runs/SIGMA-RULE-FEATURE-PARITY/final-source/crates/quoridor-ai/src/lib.rs SHA5ab5eca5c23814dbaa0162b25e8fe710e58cdb7139c0fa4e3e2f794dc041555a、固定Sigma .artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/mcts_worker.original.js とgame.js、.21frozen全ply原raw。報告.27 SHA2f50be3549581c51999a61d51376c1a4ddd2e296b86f2fa613be5fd138698610、analysis SHA2fb167808e763c986add7909c6e58abc082c8c6a214b96b2a2e35fc08ef41c93。current .26コピーkernelを基準にしない。

許可実装は新 .artifacts/ai-sigma/analysis/SIGMA-ROOT-SELECTION-ABLATION/ の短いexport/比較/診断script、sourceと原function抽出差分、docs/reports/ai-sigma-hypothesis-root-ablation.md。専用temp/cache /home/vscode/.cache/inference/research/ai-sigma/root-ablation/。既存rustc1.98.1をCPU0でstd-only短診断binへcompileしてよい（Cargo/依存導入なし、120秒以内）。入力はstdin/固定ファイルへf32bits/u64/u16を渡し、rootedge (action,prior,visits,value_sum) の形と合法順・float丸めを維持。NativeRust算術とJSNumberが同精度だと仮定しない。JS版補助はMath.froundまたはRust出力との検算が必要。

結果前gate: 全取得可能765candidate roots（native371/Wasm394、無応答欠測1は除外数明記）の元finishを visits→prior.total_cmp→seed hash で再構成し、実checkpoint Actionと一致を確認。late game5のprivate checkpointとacceptedの分母を分ける。選別削除なし、欠測や一致しない根は保存して原因判別、baseline不成立時はcounterfactual主結論を保留する。seed1979/tie hash wrappingu64を原sourceどおり保持し、action対応・prior/value f32bits・finite・visit和=sim−1を検査。元selectはQ0(unvisited)またはvalue_sum/visits、score=Q+1.5*prior*sqrt(N+1)/(visits+1)、同scoreはseedでありprior tieではない。finishとは別関数。実際の次selectは記録がないためbaseline仮想1選択を観測選択と呼ばない。

同snapshot/N=sum(edge.visits)で baseline と (a)Cだけ1.5→1、(b)sqrt項だけsqrt(N+1)→sqrt(N)、(c)score同値tieだけseed→既存合法順first、(d)finish最大visitの同値処理だけをprior/seed/firstに分解して比較する。規則セットをまとめて変更しsinglefactorと呼ばない。候補順のfirstと参照Stateの合法順firstは別因子、参照順が欲しければprefix合法replayから136方向→209着地点へ写して別集計し、order変更として記載する。reference rootedges/PVは存在しないため生成したことにしない。

FPUはSigma parentQ−.2sqrt(visitedPriorSum)が必要。root eval/value_sumが実rawから回収できなければ子edgeの平均で勝手に補完しない。既知prior/visit/parentQを明示した少数人工oracle rootsで、候補Q0とこのFPU単独を比較し数式に従う機能例として別報告する。parentQ=0等を実測値と称さない。oracle rootsは結果前に固定し、同score/zero visit/near tie/negative value/±0/seed/orderの境界を含める。

全rootsとmatched97集合を別々に、各因子のargmax変化数・score差・同値/near tie・unvisited選択率・分母/欠測を保存。source上の式差と機能差/不変、float精度と順序、最終snapshotで変化しない場合の限界を説明。fullsearchではvisits/value/NN経路自体が変わるため「不変=H2全否定」「変化=棋力改善」としない。次の実NN/同sim ablation案は新契約の提案のみ、.26へPUCT修正を自主依頼0。

保守起点issue作成00:58:01Z、処理停止01:25:00Z/提出書込停止01:35:00Z/global04:00内。01:22以降新job0、stopJSON/自己PID0を先保存、最終短報告<=2000字+JSON。CPU0単1/RAM1GiB guard.875/new32MiB guard28/GPU0、短runtime各45秒/compile120秒か残枠の小さい方。experiment .26準備2,4/jobs2/RAM4・診断2と並行しroot含め3LLM、CPU<=4/RAM<=8/newstorage12GiB維持。単なる機能診断で性能窓なし、監視/競合の限界を記録。

privateTMP/XDG/短aliasrealpath/PIDstarttick/全child wait・RSS/affinity/exitを保存。pause/guard/期限で自己group停止、他者kill0。修正は原因別1回以内・元予算、失敗source/log保持、原証拠/model/cache/入力削除0。ready/show目標/.28/.27、pauseなしなら自.28claim。.27は統括限定分析受入れnotesを確認し本人close可、未確認/旧失敗保持。他者/goalclose0。終了show/backup/report --issue quoridor-4lc --to coordinator。実装難なら数式照合/限定反例と未完了を返しscopeを広げない。
