# ブラウザ対局のプレイヤー専用探索Worker

2026-10-02、ユーザー「その方式に切り替えるように指示して。」による現行方針。現行枠7の期限・物理資源・固定モデル/参照探索は変更しない。本書は旧単一探索Workerと、全手で前Workerのzero ACK/診断取得を待ってから相手時計を始める実装方針を置換する。旧run/成績と原110/111の検証条件は変更しない。

候補AI(C1.5の既immutable pending Wasm)と固定Sigma(C1/FPU.2/temp0)へ探索Workerを1つずつ割り当てる。C1候補は110の未採用研究variantなので今回の基準へ黙って使わない。各Workerのモデル/session、探索handle、世代、局面binding、暫定手SABと故障状態を分離する。mainは手番/局面/合法性/勝敗/締切と手採用を管理し、外Nodeは起動/順次実行/外資源監視/障害回収/終了後保存だけ。毎手Node時計/審判/CP通知/必須事後replayへ戻さない。

## 手番と旧処理

新探索を始めるのは手番のWorkerだけ。mainは完成CPをSharedArrayBuffer＋Atomicsのbounded readで取得し、合法Action/局面更新/必要な小応答を確定する。確定後はその手のSABを更新不可・新評価開始不可にし、進行中の推論だけを終了・回収する。取消状態をmessage到着だけに依存させない小control/世代検査を実装できる。完成前・旧世代・他プレイヤー/局面の結果を採用せず、確定後の結果で公開手を更新しない。残推論を次探索の木/history/cacheや評価へ再利用しない。

mainは手確定/局面更新後、相手Workerへ局面を渡して相手の時計を開始できる。旧Workerの停止ACK・詳細CP取得・数値解析・ファイル保存をこの順序の一律前提にしない。mainの同期診断も次手開始を占有しないよう、検査に必要な詳細は後段のqueue/対局後解析へ分ける。各Workerは自分の次の探索前に、自分の前世代を回収して同Worker重複を拒否する。その待ち時間は別spanとし、同Workerが未回収なら回収完了後に自分の新探索時計を始める。両Workerの全回収は対局/run終了・pause/abort/timeoutで行い、終了待ちを全廃しない。

先読み/相手手番中の新探索/2Worker常時探索は導入しない。確定時に既に始まっていた推論が相手手番へ残ることと、新しい思考を続けることを区別する。mainが確定後に共有制御で新NN開始を止める経路と、NN入口・返却・旧結果棄却・世代を記録し、途中NNを同期割込みできると主張しない。Worker終了時刻>500だけから追加有効思考/棋力不公平を認定しない。

## 時計・資源・診断

今回は500msを手採用の試験条件とし、最初は同T500/cutoff402/adopt411/seed1979・同RuleA/モデル/探索capsを使用する。必要な条件差は結果前にrun設定へ記す。main入力/公開予定/実採用stamp/相手局面通知とt0、各Worker NN開始終了/旧ACK/自己次手待ち/旧結果棄却、残処理が重なる時間を別に保存する。main↔各Workerの時計校正を開始/終了に記録し、API await≠kernel時刻、ACKwall≠CPUを維持する。500ms採用とモデル残処理のCPU競合・対局待ちを区別する。

全Chromeと2モデル/sessionの合算current RSS、推論各1thread、同affinity[2]で両Workerが同論理CPUを共有する条件から始める。残推論と相手探索が一時重なるCPU競合は測定上の限界として記録する。競合ゼロ/硬いOS期限を完成条件にしない。同時重い研究jobは直列化し、研究CPU4/RAM8GiB/保存12GiBを守る。資源不足なら無理に両sessionを起動せず不足として停止・報告する。正式CPU公平性/NI/Sigma同等の認定はこの小診断から行わない。

最小確認はsecure/crossOriginIsolated/COOP-COEP/既依存、各Worker/SAB/世代分離、取消・初回無し・未完成・旧結果棄却、確定後新評価抑止、相手時計開始が旧ACK前にも可能な枝、自Worker次開始前の回収、run終了の2Worker Modeldrop/ACK/timer/message/外回収。安いmock/実browser機能から同mainの動的4ply、成立範囲で結果前登録した小色交換診断へ進む。旧単一WorkerのWDLと統合しない。全過去gate/全コピー/毎run新契約/一NN窓を標準にしない。
