# 現在の優先順位と教師生成・学習計画

2026-10-03 frame13、ユーザー明示「2時間で進めて。」に基づく新配分。開始12:45:15/終了14:45:15UTC、重開始停止14:35:15、監督14:40:15、monitor14:43:15。期限正本/mainmirrorと運用92はsteward唯一writer、統括はこの計画・担当契約・Beadsを所有する。native主評価と教師生成効率を優先し、旧frame12の終了/結果/失敗を遡及変更しない。正式173の198holdoutは学習へ転用しない。Sigma NI/NNUE最高棋力は未達。

## 今枠の問いと実配分

| 優先 | 到達点・担当 | 費用と次判断 |
| --- | --- | --- |
| 主187 experiment | 185の薄gamepoolを実Rust複数handle・177のheld realGPU provider・fullgame/全手教師exportに接続。CPU worker3とactive game3/12/24を分離し共有maxB8へ多重化。同K64で最速CPUJSと実生成の全費を比較 | 実装45–60分見積、重計1800s、候補5mode各24game/各300s、計算CPU4/RAM GPU6guard5.5/VRAM6、storage256MiBは既experiment2044内。個別science14:20/処理14:30/提出14:40。実効batch/待ち/輸送/初期化/回収とRpolicy/Rz/Rjoint/全jobwallで採否。利益なしならGPUbranch終了、CPU採用経路へ |
| 小188 hypothesis | 176親から同2260train/seed18180311/200step128でLRだけ.01→.0025。旧新validation全502/8gameのπ/zを比較し代替checkpointへ | CPU8単1/RAM1guard896、science60s・1job30s/26604samples、new512KiBは既hyp20内、science13:15/提出13:27。187重NN/GPU前に終了。全game/πとzを別評価、176既定を自動置換しない |
| 条件付き次189候補 | 既2762学習教師で小value NNUEの疎特徴/差分更新とCPU学習接続 | 13:40頃に187実進展・188結果・残費/空きCPUから実配分判断。小実装25–35分＋CPU実処理<=60s/RAM1/保存256KiB目安。未登録・未開始、GPU本仕事を遅らせる全案必須gate0 |

187/188は13:01:51/13:02:03UTCに本人保存セッションへ実配送accepted。受理と本人ready/show/claim・actual scienceは別に追う。187実装と188静的準備を進め、188学習のactualstop/currentidentityを確認して187重計算を開始する。研究を92全史・全役承認待ちにしない。criticの独立検算は重大な実結果の保存を受けて必要範囲で配分し、入口の全稿gateを作らない。自然監督CPU0とのphysical窓・aggregateCPU/RAMは各ownerが直前に確認、LLMactive数は拒否条件にしない。

187は実装上必要なら科学結果前に最小mode群へ絞って理由/全予定statusを固定する。予定はCPUJS3heldsession（現在最速実用対照）、RustCPU3serial（構造対照）、GPU3/12/24activeの5mode。各samefresh24game/K64/root64edge63/同d790/温度tau1初16newply、その後argmax/200newply打切りzunknown。GPU差によるtrajectory差も保存、C++全生成規則との同一性/棋力を認定しない。各game1pending・独立tree、取消所有を返却/破棄まで保持する。新private capを明示し旧177512/17640000/185512を黙ってresetしない。実GPU未測部分B3/5/6/7は必要小parityを予算内で確認する。原ONNX batch1と私有torch実dynamicBは別に記録する。

採否はraw行数より合法・視点・π訪問・z終局・lineage・多様性を保つ有効教師/全job時間。全fault/未完了/初期化/探索/推論/輸送/記録/回収の費用を残す。対照はsameKで、探索量削減だけを品質維持の高速化としない。実装が長引けば最小実生成と保存を優先し、mock/handle増だけを実生成成功にしない。最初の本人開始・準備/科学進展をrootへ報告する。

## NNUEへの最小接続の判断

自前PVの正式Sigma同等を恒久的入口にしない。13:40頃に物理空き/残40分程度があれば、188担当へvalue-only小NNUEを1案だけ配分する判断をする。候補は固定座標313疎特徴＋距離2値を後段へ接続しhidden32 accumulator、f32 full-vs-delta/make-unmakeと手番符号の有限parity、既学習用48game2762行のz又はrootmeanを明確に分けたCPU fit。選ぶ教師・split・追加samples・費用は実配分時に固定する。rootmeanは予算付きMCTS蒸留で真値に読み替えない。差分更新の機能・value fitと速度/αβ/棋力は別にする。GPU生成を妨げるCPU5/同重jobを作らず、残費不足なら具体未着手項目と次枠費用を示す。NNUE全面移行や本PV調整の反復を今枠主仕事にしない。

## 再利用する根拠と保持する限界

frame12はCPUJS自己対局24+24game/1409+1353=2762適格行、train2260/validation502、learner/ONNX有限接続を得た。176既定checkpointを保持し181継続checkpointは代替。181新valπ2.571901→2.391096改善に対しz1.663258→1.951053悪化。186 actualCPU診断は新3/4game value退行、015の逆符号飽和集中（悪化正寄与62.9%/net95.8%）を具体化したがLR原因は未立証。新4game相関/validation再利用/追加stepと旧再露出を残し、合算総lossでvalue悪化を隠さない。188は同じ継続条件の単因子比較で、棋力改善や独立holdoutではない。

180同K800では現Rust wrapperはJSより中央値23–33%遅かった。181 finalcheckpoint削減はnew/old .9612/.8791/.9587で限定採択未達、new/JS1.2993/1.1366/1.1656。薄JSON改善を言語優劣又は教師生成採用へ自動変換しない。187同Rust構造対照だけでCPUJS改善を宣言しない。

176のGPU3/maxB2実生成はCPU188適格行21.251523s対GPU同188行54.711141sで不採用。177のB2単route2.72倍を生成倍率へ広げない。185は3人工worker/maxB8/ID/取消と実Rust2handle保存tape対応まで、fullgame realprovider未接続。今187はその未解決を実生成へつなぐ新配分である。

Sigma型の根拠は固定[751186 selfplay_cpp.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/selfplay_cpp.py)のthreadsとparallel_games分離/get_batch→GPU→put_results。既定7worker/2048game/maxbatch1024を本環境へ複製せず、歴史checkpoint実設定の証明ともしない。原C++ cache/solver/noise/PCR等の全規則との同一性は未測定として区別する。

## 運用報告と次の確認

92 frame13親SHA160ca38306c6ddaaf81b874771afd0a52f5127dd5b7924588b6fab688bf80f8e、Git1d02983c。本人報告はscheduler3534745/start28492381・monitor3534758/start28492397 running/loaded24hash一致、旧identity現在不在。初回officialturn completedは点検全成功とは別、現在source停止の報告を受領。運用binding編集/92依頼再配送0。次14時台の停止責任は同92 owner。

supervisorのframe12知見（全費と適格教師、π/z交換、多様性因果交絡、CPUJS対照）を187/188へ採用。実改善の点検は188全game結果、187新実生成の採否/全費と有効教師に置く。新監督層・全測定checklist・全役相互承認は増やさない。個別未支持/未完了でも科学/source/子停止と必要データ/Git復元/Beadsbackup後に有限受入れclose、goal未達は維持する。
