# SIGMA-C-FACTOR-BROWSER / quoridor-4lc.110

契約1・枠7。experiment、受領2026-10-02 07:51:26 UTC。処理08:55／新run08:50／提出09:05を維持。**等completed探索は有限なC感度を支持。C1の探索診断は0勝0分4敗で、改善・係数採用は支持しない。** 正式公平性／NI／Sigma同等／actual_goは未認定。旧107の結果とは統合しない。

実行sourceは `0f0597e73e5444c2a576121242a02e18417aad01`、元版は107 `ec4e92d`。共通責任分類の修正と停止処理修正を両係数へ適用し、係数の差とは区別した。Worker探索＋SAB、browser mainの時計・合法性・対局・結果収集、外Nodeの起動・資源監視・終了後保存という分担を維持した。Node審判・必須事後replayは追加していない。

## Buildとbaseline parity

既toolchain/cacheで `cargo build --release --offline --locked --target wasm32-unknown-unknown --lib`、CPU0／jobs1／private targetを使用。baseline/C1のRust source差は `PUCT_C: 1.5 → 1.0` 一行のみ。Q0、sqrt(N+1)、seed1979、finish/order/tie、RuleA、caps、モデル・NNkernelは維持した。

- baseline：292,139B、SHA `1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01`。元immutable Wasmとbytes一致。
- C1：292,135B、SHA `8438310cf8f7d096bd84364a03b97f99f737ca0a9be6c2812a7ecdee3d92d9dd`。

ブラウザ内でoriginal/rebuildの3固定context×K8を比較し、完成CP全fields/tree、648features bits、137NNの固定混合閾値、NNcall数が一致。rootのfinite／strict value／合法順／P2／Action-prior検査も保持した。単なるWasm.validateではない。

build-r1は必要research.rsの不足で失敗。r2は同package・targetの再利用によりC1が再compileされず、baselineと同binaryになったため不適格と記録した。このbinaryでC1検索は実行していない。r3はtargetを分離して成功。失敗・command・各版は保存し、NN負例へ変換しない。

## K32の実探索

結果前にinitialはbaseline→C1、asymはC1→baseline、jumpはbaseline→C1を固定。6検索すべてroot展開を含むK32 completed backupへ到達し、各root N=sim=32、edge訪問和31、各NN32、terminal/noNN backup0、cap到達0をbrowser内で確認した。名目192backupはSigma loop32や500ms対局とは別条件。

| context | Action baseline→C1 | 訪問数が変わったedge | 訪問分布TV | entropy baseline→C1 | 最大深さ baseline→C1 |
| --- | --- | ---: | ---: | --- | --- |
| initial-p1 | 13→13 | 0 | 0 | .550354→.550354 | 8→8 |
| asym-hv-p2 | 67→67 | 2 | .064516 | .239217→0 | 7→6 |
| straight-jump-p2 | 31→131 | 3 | .225806 | 1.707492→1.750663 | 5→3 |

6行のwhole count wrapperは3187–3673ms。特徴・NN・checkpoint・treeコピー等を含み、純NN速度比や改善とは呼ばない。最初のbaseline K32は探索結果とModel zeroを保存後、inner cleanupが `OWNED_REGISTRATION_REQUIRED_BEFORE_SIGNAL` で失敗した。outer owned回収はremaining0。6根の測定のうちcontroller成功5／失敗1として残し、良い行で置換していない。修正版は監視読取子を停止・await後にbrowserを回収した。

## 新分類と探索用4局

同時SAB FAULTとlate／Judge／cancel／external abort等の全flagsを保持し、browser基盤の原因をshared FAULTだけでengine lossへ上書きしない。原因不明のshared faultは共通基盤unfinishedへ保留する方針を8小browser mockで確認した。旧107の4局を再分類していない。

C1対固定Sigma、initial／asymの各候補色1→2、seed1979を結果前登録。4game cap到達で停止した。

| 入力／候補色 | 結果 | 理由 |
| --- | --- | --- |
| initial／1 | L | 合法goal |
| initial／2 | L | initial_no_completed_cp責任loss |
| asym／1 | L | 合法goal |
| asym／2 | L | 合法goal |

計291公開、290合法手／初回eligible CP無しnull1。browser late0／infra unfinished0、最大public447.760ms。null手はroot features／NN検査を通過したが、最初のCP完成・受信が402 cutoff後で共有暫定手にならなかった。root準備span236.810ms／API await110.560msを保存しており、この不足をNN不一致やAPI内核遅延だけへ帰属しない。prior／完成CP検査はその1行で未成立。

baseline rebuildの同classification小動作確認は2合法手。Worker停止区間lower>Dが1、ACKwall>500が1、402後NN開始の可能性1／公開後開始確実1を残した。C1の4局ではWorker停止upper<=D286／lower>D5、ACKwall>500が5、公開後NN開始確実0。Worker停止・配送ACKwall・API awaitは別欄であり、CPU時間や正式公平性へ読み替えない。開始・終了のmain/Worker校正は保存、途中driftやOS硬締切は保証しない。

## 分母・停止・保存

通常機能／探索要求14、診断game開始4。startup9session×6=54NNは別分母、手内／検索NN1469、実NN計1523。通常公開計293（baseline2＋game291）、fixed参照root6／動的自己整合287、prior完成292／欠測1。count/parity根の固定参照12は別分母。全深部NN一致・一般tree安全性は主張しない。

08:27:54 UTCにsource／NN／Model／browser／監視callback停止を本文前に固定。13jobのremaining／unknownは全0、記録783identityは現在不在。初回inner回収失敗とouter owned waitを分けて保持し、自然停止／全期間保証にはしない。browser wall297.634s／build14.081s、最大current RSS1,645,355,008B、runtime保存peak55,328,768B、build保存peak38,301,696Bは配分内。ru_maxrssは過去highwaterとして別記。40ms瞬間peak、背景SMT、終了子CPUの欠測を0補完しない。

[停止証拠](../../research-data/ai-sigma/110-c-factor-browser/handoff.json)のstop SHAは `bd2029a9fbf151153c3ad1ab75a8def502c6c9cf3e286be04febc48d87ab9263`。[archive manifest](../../research-data/ai-sigma/110-c-factor-browser/archive-manifest.json)は296ファイルのstream復元hash一致を記録する。2binaryと必要rawは独立111が読めるよう保持、所有停止後のprivate build targetだけ整理した。再現は新run名・現在の許可／deadlineで行い、旧runへ上書きしない。

停止版・必要データを独立111へ引渡し、原4gameのbrowser保存replayとasym/jump×係数K32の有限確認を待つ。通信受付は研究受入れではない。追加実験0、係数採用0、正式NI／Sigma同等未達。
