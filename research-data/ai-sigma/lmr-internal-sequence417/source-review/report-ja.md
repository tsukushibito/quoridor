# 417.3 内側N／R手順の限定source確認

`source_clear=true`、未解決blocker 0、ordinary 0。評価対象は凍結417 packet `342887a9…`／binding `146d64b5…` と、Root `445f5d71…` の一式だけのconsumer型修復である。原packetのE0608を成功へ書き換えない。software完了、数値／費用／棋力／既定採用の判定ではない。

immutable Git `0252dd5a81ab8e65e92dc8f9b2d2bf90c9fd0bee`、六before gzip、forward／inverseから七subjectをメモリ内で再構成した。六postimageと旧416 moduleの削除が一致し、inverseは全beforeと新module不在へ戻る。三外部fixtureの差分はcfg `trial_trace: None`だけ。Pythonは変更対象ではなく、既存のstrict opt-in／完全prefix入口を再用する。Main／Git index／Cargo／対象sourceへの書込み、target import、native／test／Search／model呼出しは0。

| 境界                 | 独立に確認した根拠                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| slot選択・元探索隔離 | `lmr_observation.rs:138–309`。iteration5／d3／ply2のみ。H0はeligible q0・rank4..8を返値前に予約し、H+は完了したq1 fail-lowだけを選ぶ。各仮説で親完全履歴を変え、全slotで親履歴＋actionを重複除外する。予約を置換せず、不足slot／中断を保持する。rootのD5完了フラグに加え、runnerは通常return検証・親復元を通ったCOMPLETE D5でなければ全armを未実行にする。                             |
| 同一の親・履歴・窓   | 同module `496–595`。元rootをcloneし、captured colour/action pathをchecked playで再構成する。盤面・STM・rules・total ply、base＋overlayのaggregate `count(key)`を双方向に照合する。opening4手のcountをdivergence履歴へ流用しない。保存したpost-TT／pre-child alphaと既存`next_up`、親ply2を共通childへ渡す。符号反転は既存childが所有する。                                             |
| NとR                 | `alphabeta.rs:3051–3090`。Nは`child` depth2を一度、Rは既存`reduced_child([2,1])`を一度呼ぶ。Rのshallow>alphaだけが同じstate／TT／ordering／scratch／generation／start／statsでdepth2確認へ進む。再初期化や100K予算の復活、親full-window確認はない。各arm間は新しいTT／history／scratchで独立する。                                                                                     |
| depth・中断・復元    | 同 `3091–3169` と`LmrStage`／`LmrTrialTrace`。R fail-lowはprotocol COMPLETEでも実返却depth1、target2を別に保存する。shallow完了後の確認cap／cancel／errorは最終UNKNOWNで、最終値／boundをnullにする一方、完了したshallowと既知の累積仕事を残す。true goal／threefold、enter／control、canonical make／undo、NNUE terminal skip、context／board／path／child slot復元は共通処理のまま。 |
| 時計・分母・consumer | `measurement.rs:1702–1999`。N/Rとも準備後のdispatch直前からResult取得直後までをkernelとして測り、`?`より先に終端時計を保存する。wholeはarm関数の外側で再構成・allocate・局所drop・復元検査を含み、JSONと返却recordの後日のdropを除く。各stage仕事はarm仕事に内包され、root／arm／明示childの件数を分ける。未実行armの値・時計・仕事はnull、repeat driftはDIFFERENTとして残る。         |
| OFF・必要費用        | 通常入口は`Search::<false,false>`。snapshot／scan／heap／per-node clockの新処理はOFFで実行されない。ONでは最大4親context＋長さ2のpath、固定6 frames／8 coverage cells、armごとに二stage trace、親replay／count照合、新規TT1M／history／scratchが必要である。root採取とarm traceは別const経路で、arm中に枝選択を行わない。実layout／RSS／時計分解能／速度利益はUNKNOWN。                |

`boundary-correspondence.json`では、`root_depth/reduced_child/lmr_allowed/control/enter/key/next_up`のbefore／afterを独立にbyte比較した。childは二つのconst TRACE hook以外、negamaxは空slot label以外がexactで、weighted `same_history`の所有関数もexactだった。Rの状態共有はこの同一関数の直接dispatchで確認しており、偶然のTT hitだけを根拠にしていない。

Root型修復はoriginal-stage projectionの`map(Option<Value>)`を`map_or(Value::Null, ...)`へ変える一式だけである。凍結measurementを一式置換した結果がimmutable Git `445f5d71a93b8e42581cfe11f822be6c252c1c97`と全bytes一致した（SHA `1277904f…`／96610B）。Someのstage object／NoneのJSON nullを維持し、欠測比較がUNKNOWNへ伝播する。current mutable Mainは読んでいない。

新8AI／2runner定義は、Rの1段／2段、連続したnodes/evals、共有cap、第二段のerror/cancel、N-R-R-N独立、D5未完了拒否、異親／同枝除外、null／repeat drift／boundを区別する。旧成功suiteは実行していない。Rootから、原BUILDv1 FAILED 13.589924963991507s内でAI8が実PASS、runner assertions前にE0608、修復後の残softwareはpendingとの事実を受けた。本レビューはそれをsoftware全成功へ昇格しない。runnerの実feature名`measurement`によるAI research-diagnostics転送はRootの機械的caller解決として分離する。

上限は12 root＋48枝×4arm＝204 top-level、root＋明示childは最大300、総node cap31.2Mであり、実仕事量ではない。N/Rのtargetは2/1で、設定上のDepthRankを新しいWDL oracleや歴史的warm再現へ変換しない。この固定armの子孫depthは2以下で、通常LMRの入口d≥3には達しない。Rが外側で明示する一段削減／確認と、元rootのLMRを混同しない。

唯一の私有helper修復は、forwardがGit `diff --git`付きだと仮定したexcerpt選択を、実際のunified `---/+++` ownerへ対応させたもの。最初のstdout空のreceiptを残し、source検査成功とは扱っていない。producer修復・native再実行はしていない。全22選択参照の前後SHA／size／modeは`selectedrefs.json`、source読取の実STOP／直接回収／fresh identity／handles／TMP／leases／owned[]は`STOP.json`に保存する。一時source captureはhashを残して回収済み。全LLM／source／admin費とcontinuous peakはUNKNOWN、既存pause／defaults／models／RAW／FAILED／費は保持する。
