# Rust主体のOthello UI

othello-wasm/src/ui.rsのControllerが、確定盤面・対戦方式・人間の色・strategy・合法操作・
パス・終局・保存可能性・新規/再開の確認・非同期token・fullModel固定identityを所有する。
ルールは既存othello_core::GameStateを直接使う。core/evaluator/search/model/native APIの数学は変更しない。
既定はローカル2人と簡易AI。明示的な2種の探索は[ブラウザAI接続](browser-search.md)に従う。

OthelloUi.dispatch_json(actionJson)は{view,effects}を返す。
bridge/src/ui.tsが型を持ち、createUI()が遅延初期化とfreeを所有する。
別TS session/rules/controllerは作らない。DOMはRustの表示と操作許可だけを投影する。
effectはconfirm/readSave/writeSave/think/cancelWorkerと、明示local File用loadModel/resetModel/forgetModel。
hostはFile handlesを保持するだけで、局面・合法性・model選択の権限を持たない。

保存枠はothello.game.v1。envelopeはversion1/game othello/mode local|ai/humanSide1|2/
strategy simple|searchV1|fullModel/state。strategyが欠ける旧保存だけsimpleと解釈する。
fullModelだけversion付き固定modelIdentityを追加する。Fileやweightは保存しない。fullModelはAI対戦専用で、ローカル2人への変更ではsimpleを使う。
新規は確認成功時だけ保存枠を置き換える。再開はGameState/strategy/identityをRustが検査し、
fullModelではlocal Fileの再選択確認まで元raw保存を保護する。
pending・破損・失敗した再開中は、手動保存・着手・teardownでも上書きしない。
書込失敗を同じtokenでRustへ戻し、保存済みと表示しない。

要求はRustのgeneration/request、原state、strategy、fullModel identityで照合する。
通常fullModel応答と人間の合法手はrequestだけを失効させてidle Workerを再用する。
新規/resetは実ゲーム境界でclearを予約する。取消・incompatible setup・File変更・再開・disposeは
同期的に権限を破棄し、hostがlistener/timerを外してterminateする。
古い返信は盤面や保存に適用しない。同期Wasm内部取消やfreeをterminateから推定しない。
lazy import前にteardownを登録し、遅いowner生成はfreeする。route disposeはFile handlesも放す。

DOM契約は既存new/resume/cancel/retry/pass/saveとboard data-index/data-legalを維持する。
明示fullModelのFile入力はothello-full-main/othello-full-ending、準備buttonはothello-load-full、
statusはothello-model-status。main data-ai-phaseはidle/initializing/thinking、
data-model-statusはunloaded/loading/ready/error。内部探索診断や棋力表示のframeworkではない。

今回のsource定義はmodel-free Rust5件とtransport/Worker/host fixture7件であり、authorではUNBUILT/UNRUN。
Rootは変更したUI/save/token/lifecycleと実生成ABIを関連範囲で検証する。
source fallback宣言を実生成typing・実Wasm・実描画の代わりに数えない。
共通home/chooser/Quoridor、旧core成功suiteや実model/scienceの再演はこのsource作業に含めない。
