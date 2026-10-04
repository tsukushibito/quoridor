# 生成構成の独立選定 / quoridor-4lc.223

目標quoridor-4lc、frame16延長17。hypothesis223、受領時計2026-10-04 08:14:31UTC。ready/show goal+self/no pause/本人割当→claim後、08:14台に静的読取を開始（intakeの08:14:48はtool順からの概時刻）。source-read保守45s上界、新科学CPUjob/model import/torch/forward/game/teacher/test/GPU0。旧220/221の結果・期限・sourceは変更しない。

**次の最大1実装は、私有held-providerの固定B8 forwardだけをCUDA graph replayにし、partialは原eagerを使う小対照。** 現在最大の不足は、forward_syncの中でhost launch・GPU演算・待ちのどれが減らせるか不明なこと。現Node–Rust–Pythonの維持自体を目的にしない。graphが小利益なら同構成への追加調整を重ねず、配列転送＋Rust多handle pumpを次に再検討する。今回は選定見解のみで実装・実験を起動していない。

## 現物sourceと既結果から分かる範囲

221の同fresh48/B8→B24→B8は113.865/112.111/118.947s、1554joint/81096NNで仕事量対応、保存結果ではvisit/action対応も支持。B8同条件確認の変動があるため、B増だけで実用改善が確立したとはしない。平均B6.18→7.90、最後8完了span34–37sも、大きい上限Bだけでは独立treeの投入不足・尾部を解消しないことと整合するが、原因を確定しない。

provider.pyの前後synchronizeで囲まれたforward_syncは55.887–65.556s。これはGPU event専用時間ではなくCPU dispatch＋device completion待ちを含む。逐次server区間内の時間と、queue/search/write callbackの重なる待ちspanは合算してexclusive支配費にしない。provider側json_parse約2.2s、最初のJSONencode約2.6s、stdout_write約10–12sは表示された区間で、後者に二回目encode・pipe待ちが混じる。worker search_msは多数gameの重複spanでありjobwallとの差をCPU費にしない。

現wireは648 f32を整数JSON列へ、結果137f32bitsと136logits/valueを重複保存し、応答を計測用と送信用に二回json.dumpsする。brokerはbits/logitsの対応をJSON.stringifyで検査する。Rust begin/resumeもserde_jsonで、pending leafにfeatures・legal・history・pathを返す。Nodeは毎leafを受け共通queueへ配送する。構造上、packed arrayとrootfinal-only metadataで減らせる複製がある。しかしbytes削減からwall短縮率を断定できず、Node parse表示だけは小さい。providerStop.pipeの約307MBrequest/161MBresponseは既記録値、Rust3bridgeの多量responseも保存値から確認した。

既Rust Search/Registryには独立複数handle、onepending token、generation、真平均root、terminal-noNN、cancel/freeがある。C1/FPU.2/f64/firsttie、root64/edge63を変えずhot transferを私有版へ置換できる候補。手番viewはSigma648の縦反転、136policy（8pawn方向+64H+64V）とRust209action（81destination+64H+64V）のlegal mapping、履歴付きRuleA、tau/seed/π/rootNN/rootmean/z/lineageが教師境界。QF1の180度特徴をSigma入力へ読み替えない。

## 同じ候補集合の比較

| 候補 | 再用・必要差分 | 品質/検証費と今回の順位 |
| --- | --- | --- |
| 私有CUDA graph replay | 同d790 foldedf32/TF32AMPoffのB8演算と固定input/output buffer、partial eager、既heldsession保持。capture/startup/sampleとVRAM別計上 | tree/transport/teacher定義を触らずlaunch混合区間へ直接介入。最小数値・ID・stopと同fresh全job対照で判別できるため第1。host launchが大きいとの証明はまだ無い |
| 配列転送＋生成向けRust pump | Registryを使う少worker/多数treeをRust内でbegin/resume反復。Nodeはgame開閉・rootfinal journal、NNはlength-prefixed frame/IDとcontiguous648→137f32。Pythonheldproviderへbatch配送 | 共有queue構造は既にある。新geometry/探索則なしで輸送を減らせる有力代替。変更はRust/Node/Pythonの複数境界・部分read/cancel/order/error/guardへ及び、未計測輸送費に対する開発回収が不明。graph小利益かtransportCPU/criticalpath証拠が強まれば優先を入替 |
| activepool拡大 | 同workerあたりhandle追加、供給game増、refill | B増だけと異なる供給・尾部因子。ただし新arena/RAM/履歴・fairqueue等の実headroomが必要。尾部spanはゼロにできるexclusive節約量ではない。steadyが供給律速と判別されたとき再検討 |
| ローカルSigma C++生成基盤 | threadsとparallel_gamesを分けget_batch→GPU→put_resultsする設計を再用可能。board/BFS/arena/queue/array interfaceは参考候補 | 現物C++ source/built extensionの既known対象pathでは用意を確認できなかった。host全体の不在ではない。未改変selfplayはTT/virtual-loss/leafparallel/noise/FPU/PCR/solver等の教師条件が異なるためfaithful教師と等価でない。利用可能現物と同規則への薄設定範囲が提示された場合は順位再検討 |

C++の構造は固定751186を既183が公開一次source閲覧した記録と、初期調査のengine/selfplay比較をreadonly再用した。今回はC++原文現物の再確認ではなく、この証拠の限界を明記する。今回直接読んだ一次sourceは現Rust/Node/provider/foldedadapter。cachedWeb仕様は既調査の参照である。既fixtureの即時source一覧と既reference対象pathを限定rgで探しただけで、新取得・import・compile・host全cache監査0。C++再用を構造参考に止める理由は言語ではなく、現物準備と規則差分が未確定なこと。

C++経路を実教師に使う将来の確認は、同9x9 pawns/wallsegment/rem/history、P2view、136action/value、K定義とrootedge、TT/cacheのhistory安全性、noise/FPU/PCR/solver/leafparallelの設定対応、π/rootNN/rootmean/z/lineage保存まで。無効化してもtie/terminal/backup/NN呼出回数は有限fixtureで合わせる。K800や同名Sigmaで品質等価としない。全C++移植は今必要ない。

## 次1の有限実配分案と判断

これは提案であり223本人の新heavy許可ではない。開発・検証見積は計画上の上限案、実績・実用readyではない。owner私有版で20–35分の実装打切り、5–10分の小preflight/parity、次に割当可能なら同fresh48/K64/B8のeager→replay→eager各120s以内程度を想定。全stage/capture/sample/失敗/coldinit/qualification/pack/Gitを含む費用を記録し、existing221cap残へ自動加算しない。捕捉未対応ならtyped停止、共有環境変更や巨大graph基盤へ進まない。

固定B8の頻出forwardにだけ介入し、B1–7はeagerfallback。captureの準備forwardやbuffer検査もwarm/sampleを隠さず別課金する。B拡大、active変更、転送binary化、TF32/AMP、モデル・探索・tau/種・lossは一緒に変えない。capture内の操作と同期/入力copy境界を私有sourceで確認、GPU eventの演算区間とhost経過を並記し双方を加算しない。出力bufferは次replay前に独立snapshotへ、ID/tokenへの対応・部分batch・取消後discard・全wait/guardを有限確認する。

まず異なる入力の全136logits/valueをeagerとabs1e-4+rtol1e-4で確認し、f32bits/ID/STM/順序を保存。数値許容対応は離散MCTS等価の証明とは別。rootfinitefixtureと同fresh全gameの合法/π/edge63/z/全fault・実NN総量を確認し、差があれば原因とteacher変更を分ける。主判定は適格joint/全attempt全工程wall、資源・coldcaptureも含む。単forward倍率だけで採用しない。

実利益がB8確認の揺れ程度、又はcapture費を含む予定生成量で回収できなければ枝止め。hostlaunch削減が乏しければ配列transfer/pumpへ主問いを移す。CPUdispatch/transportが小さくGPU演算が大半なら、言語変更を優先する根拠は弱まり、入力供給/モデル演算の別配分を判断する。いずれも新実測が必要で、既spanだけで断定0。

## 全費・将来回収局数

221保存のqualification/pack/Git込み1000局外挿は約40分付近で、実1000完走でも独立データ増量でもない。現48の32.375joint/game、開始mix/長さ/尾部/固定費の外挿限界を保持する。初期60分は外挿上届く候補、次30分は概ね25%以上の全工程削減が必要という計画目安であり、graphの達成保証ではない。

開発＋parity＋失敗＋測定の追加費をC秒、同品質採用後の全工程節約をδ秒/gameとすると、回収N=C/δ（δ<=0は回収なし）。例えば追加40分で実δ=.3sなら8000game必要、1000gameだけでは費用利益が戻らない。これは想定算術で実測ではない。C++規則接続又はRust統合の大投資は、先にC上界/継続予定game/δの必要値を設定し、小部位で改善が無ければ全面移植しない。大規模教師をNNUE学習量/多様性判別へつなぐ将来予定なら、単frame内だけでなく反復利用の回収も判断する。

## 保存・射程

自域intakeに現物sourceSHA/len、受領・概開始・claimとread範囲を保存。staticread45s上界、科学実数0。新128KiB、forecast100KiB内、旧hyp58480714+131072=58611786<58720256、親追加/UNKNOWN減額0。保存時current/uniqueGit/残metadataを再確認。旧220/221/source/model/testを変更せず、defaultindex不変更/必要Gitbyte復元/Beads notes+backup/自己source-doc停止で有限引渡し。採択・実効果・NNUE最高棋力は未認定。
