# 明示的なブラウザAI

既定はローカル2人、AIの既定は簡易AI（非学習）のまま。Rust UIが対戦方式、人間の色、
strategy、確定盤面、合法手、要求token、評価ファイルidentity、保存と表示を所有する。
TSはDOM・ローカルFile・Worker・保存effectを実行する。Quoridorと共通chooserは変更しない。

## 選択肢と結果

- simple: 従来のchooseMoveを呼ぶ簡易AI。モデル不要。
- searchV1: v1 heuristicのbaseline searchをtimeMs1000/ttMiB32/maxDepth64/exactEmpties12で呼ぶ。
  モデル不要で、既存SearchResultを返す。
- fullModel: 「フル探索AI（評価ファイル使用・1秒）」を明示選択した場合だけ、
  現役FullSearchModelのsearch_jsonを呼ぶ。既存baselineへ変換しない。
  timeMs1000/maxDepth60/fixedDepth null/selectivity null、mpc/etc/stability/parity/shallowOrdering true、
  interpretation simd/hashLevel20、original_mpc_coefficients_jsonの係数を使う。
  生成・配布済みモデルの自動採用や棋力の主張は含めない。

fullModelは別型FullSearchResultの実rawScore/score/engine-disc/scoreKind/proven/実行状態を運ぶ。
Rustは元のstate/token/strategy/modelIdentity、実結果schema、予算timeoutの完成結果または合法fallback、
coreの合法手を検査する。選択的な推定を証明済みへ変換せず、nativeで観測されないfieldも補わない。
不正応答・取消・初期化失敗は表示して再試行可能にし、simpleへ自動fallbackしない。

## ローカル評価ファイルと所有

この画面で利用者が2つのFileを選択し、「評価ファイルを確認・準備」を押す。
Rustが発行した固定identity/サイズをhostがSHA-256で確認した後、Workerへ一度だけtransferする。
主評価は38243826 bytes / SHA256 0a8acbcbc23067933627f1bcc83c3f7ae6b7ff3e603d174a3364271fcaeeef2f、
終盤手順評価は472392 bytes / SHA256 bd908885e8bb85e72a9be2b0399f8ca52ed40a138bcaaecca3d13710945b9a93。
ファイル名は信用せず、upload/download・公開hosting・bundling・registry・localStorageへのweight保存をしない。
元ソースのライセンスとweightの配布許諾は別であり、この接続は配布許諾を主張しない。

準備（File読込/hash、Wasm初期化、construct/decode/clear/ready）は30秒の独立した上限を持つ。
ready後の要求dispatchから親の返信guardは1100ms、engineの思考予算は1000ms。
この時計を同一視しない。preCall通知は親が観測した段階であり、同期Wasm内部への進入証明ではない。
TTは実結果のttBytesを32MiB以下としてRustで検査する。現在のhash20の受入観測は25165872 bytesであり、
sourceラベルから実測値を捏造しない。

fullModelの通常応答後、人間の手番中も同じidle Worker/modelを保持する。
per-request listener/timer/authorityだけを終了し、新規対局の確認時にresetを予約して次の使用前にclearする。
毎手clear/decode/巨大Fileコピーを行わない。取消・設定変更・File変更・再開・route disposeは
同期的にtokenを失効させ、listener/timerを外してWorkerをterminateする。
取消後の明示retryは、保持したimmutable Fileから新Worker/modelを準備する。
postMessageで同期Wasmを中断する方式ではない。terminateは内部interrupt/free/即時メモリ回収の証明ではない。

## 保存と検証

othello.game.v1を維持し、strategyを明示保存する。strategyがない旧version1だけはsimpleをschema defaultとする。
fullModelだけmodelIdentity={version:1,mainSha256,endingSha256}を保存し、Files/weight bytesは保存しない。
不明strategy、不正identity、壊れたGameStateは拒否する。開始・再開は明示確認を維持する。
validなfullModel再開でもlocal File再選択と確認が済むまで自動検索・保存上書き・着手を止める。
破損・pending・失敗した再開は、手動保存やteardownでも元raw保存を維持する。

新規model-free定義はRust ui::tests::ui*full_model_fixture* と
games/othello/tests/unit/full-model-ui.test.mjs。transport fixtureは実engineの証明ではない。
既存browser-search.test.mjsのfake portはdisposeと未使用fullmodel exportを補う。
共通othello-lifecycle.test.mjsのpostimageはRoot向けのport形状更新提案であり、既存assertionは変更しない。
source担当はscoped rustfmt/Prettier/静的逆変換までを担当した。
変更UIの関連software、実生成宣言typing、現在のmatched bundleは
[通常software資格](../../../research-data/othello/strong-ai-n96/current-ui-fullmodel1s-affected-software-result-v4.json)で検証済み。
実Workerと現在のUIを通る有限consumer条件は、softwareと別に受け入れる。
旧core/evaluator/native18/browser33等の成功再演をこの接続の資格に代用しない。

実consumer確認のtest ownerは、同じVite previewを所有して起動し、起動からHTTP body完了までの
絶対30秒以内にdirect loopbackの実GETを確認する。status200/text-html・64KiB以下・現在のindex entrypoint
markerを満たしてからPlaywrightを開始し、Playwright側のwebServer所有は設けない。
whole240秒、Playwright global230秒、モデルready30秒、ready後reply1100msは別の上限である。
leader終了後のgroup signalを止め、残descendantsは既存外側guardianの回収に従う。
[限定source/software資格](../../../research-data/othello/strong-ai-n96/current-ui-owned-http-source-and-admission-v1.json)は、
実appの4 Search/2 constructor、再利用・取消・Retry・保存の受入結果そのものではない。
旧setup失敗と未報告の実Search数NULLを保持し、standalone rehearsalや自動再試行はしない。
