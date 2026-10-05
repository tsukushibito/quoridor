# frame22 αβのNNUE差分バッファ再利用 / quoridor-4lc.275

275本人の実装・自己検証報告。統括の独立採用レビューは別。mainは編集せず、managed `.worktree/frame21-search` のAI/NNUEと専用example/testを変更した。科学とRust source書込は2026-10-05 12:40:01 UTCの最終測定後に停止した。最高棋力・学習利益・全教師生成倍率は未認定。

## 結果と採用候補

**最終採否はmain追加見送り**。最終系列の方向が安定せず、共通scaffoldを除いた元production全体比較も未実施なので、新しいhookの保守費を正当化しない。統括の独立readonly sourceレビューは同算術順/parent不変/深さ別lifetime/unmake error復帰を有限支持し、性能支持と分ける。試作の有利runだけを採択しない。source/tests/resultsは比較専用で保存し、NNUE幅・実caller分布が変わった時の再検討資料にする。これはscratch方式一般の棄却ではない。

比較した候補は、探索がply別に保持するFT accumulatorの二つの`Vec<f32>`のcapacityを再利用する変更だけ。親accumulatorを不変に保ち、同じfeature追加・除去順で子を上書きする。Modelの数学、STM距離/標準化、RuleA、terminal、全合法手、ordering、TTの全history鍵/depth/bound、制限は変更していない。NNUEモデルは既存のf32固定版。

試作版では葉dense入力の再利用も比較したが、差分再利用への追加利益が安定せず、源を先に保存して最終production APIから除いた。FTのfeature構築・距離map・演算は引き続き実行する。delta_updates減少やNN呼出数減少は主張しない。

| source版・測定              | warm / steady | 差分再利用の時間比 | 葉入力も再利用 |
| --------------------------- | ------------: | -----------------: | -------------: |
| 二候補 r1                   |         1 / 3 |           0.987815 |       0.977001 |
| 二候補 r2・開始順反転       |        1 / 15 |           0.978188 |       0.982508 |
| 最終差分のみ r1             |         1 / 7 |           1.001267 |       削除済み |
| 最終差分のみ r2・開始順反転 |         1 / 7 |           0.956850 |       削除済み |

時間比は各固定rootのsteady中央値を合計し、同binary内のowned対照で割った値。最終二回は約0.1%増と4.3%減へ振れ、局面別・paired幅にも比>1がある。小さな費削減の観測は残すが、安定した節約率を保証せず現在mainへ採用しない。良い試作値だけを最終版の成績にしない。owned対照は新しいSearchの共通枠を通るため、元production binaryとの差を直接測った結果でもない。各rootのmin/median/maxとpaired幅は[comparison-analysis.json](../../research-data/ai-sigma/frame22-search-efficiency/comparison-analysis.json)に全保存した。速度equivalence marginは後付けしていない。

固定4root、同履歴・モデル、深さ2、node上限1500、CPU番号3単1で、二候補320searchと最終192searchの全512検索が完成した。Action/value bits/PV/完成snapshot/processed/evaluations/delta_updates/TT/PVS/terminal等のカウンタ・根復帰がvariant間一致し、初期profileの同depth2完成snapshotのAction/value bits/nodesにも一致した。全deep/minimaxや棋力の独立真値認証ではない。

## 選定根拠と次の問い

最初の4root D/L・最大深さ3/node4000のcaller profileは、Lのadvance_contextがroot時間の44.64%、evaluateが20.81%、prepareが0.0324%。Dはadvance約1.43%、evaluate約7.95%。Lのdelta_updates 15992に対しNN評価14554で、両者を同じ呼数にしない。inclusiveな内部処理を独自のBFS/feature/排他的allocation費へ割り当てていない。

この短いprofileのLはTT hit97/cutoff0。浅いentryがorderingへ使われたことは保存しているが、手跨ぎTTを方式全体として棄却する根拠ではない。大きいgainを期待した改変の追加や深さだけの増量は行わなかった。次の最小単位は、advance内部のencode/maps/ID構築費と**同合法sequenceを辿る際の全history鍵・必要深さ・同model世代に合うTT再利用機会**を比較する安い診断。保存済みのhit97/cutoff0/15992delta/14554evalからcaller費は問えるが、内部allocation/BFS/cross-search有効depth hitを復元できない。新しい計測が必要なら、専用exampleでdisjoint内訳と機械選択した合法sequenceを1短jobにまとめ、モデル数学/履歴鍵は維持、compile60秒・科学30秒・最大12000NN/32000nodes・64KiB保存程度を見積る（新許可/配分ではない）。内訳測定のobserver費とTT機会の診断を速度利益・教師倍率へ読み替えない。履歴を捨てたTT圧縮を提案しない。

MCTSは別担当の推論支配枝。旧271のCPUORT固定root infer API99.1%をαβ改善の教師倍率へ変換しない。新モデル・arena・学習・追加教師・GPU jobを起動していない。opened test/173正式198は読んでいない。

## 実装と検証

変更sourceは停止receiptの4path。`delta_features_into`は親のmodel/shape/finiteと入力featureを先に検査し、targetのcapacityを保って二つのVecをcopy/update、feature/fingerprint/mode/mapを上書きする。targetの以前のmodel/幅は使わず、parentは不変。更新途中に数値errorがあればtargetは部分状態になり得るが成功値として公開せず、searchは子slotを戻してからRuleA undoを行いエラーを返す。slotは検索所有で、新検索やモデル世代間に持ち越さない。

最終版のrustfmt checkと厳格Clippy（AI lib/example/test、NNUE dependencyのチェック）を実施。既存7テストはterminal/飽和非terminalの順位、PVS対exhaustive D、履歴による合法手/鍵差、partial/cancel/clock/error時の復帰、全合法orderingを確認。新3テストは全503合法子×Scalar/Simdでowned対reuseのbit一致・capacity/pointer保持・親不変、4root×制限2/1500の検索対応、update途中の注入errorの復帰を確認。最終10/10 PASS。後者のsynthetic modelと固定実モデルの検索比較を分け、現NNUEモデルのTorch再認証にはしない。

## 版・入力・費用・全attempt

固定manifest `.worktree/assets/models/legacy/frame18-native-connection/manifest.json` SHA `1b0a2998edaf7bef84e6a31634b30735b576511a96ec857c45ad429a8ac5ce6b`、weights SHA `b81792d5ba00c6d79b58cada2fc81d84ea822db48c04420b4e269fb9b71841b3`。入力prefix・同モデル・scopeとMAXは結果前登録。二候補源は`two-candidate-source.tar.xz`全member byte復元PASSで維持。初期caller-profile exampleは実行時SHAを記録したが、その時点の全example bytesを別保存していないため、厳密な入口復元についてはSHA・生結果・元library sourcepointへの有限参照に留まる。二候補以降と最終sourceのbytesは保存/復元を行う。

| 会計                       |          実績 / 上界 |
| -------------------------- | -------------------: |
| native NN（検証含む）      |      243500 / 250000 |
| 科学processed実測          |               366984 |
| tests processed保守charge  |              1200000 |
| processed合計charge        |    1566984 / 2000000 |
| 科学job                    |                5 / 6 |
| 科学guardian合計           |   1.665545 s / 900 s |
| compile/test/lint全attempt | 108.069144 s / 600 s |

modelロード・観測・guard/job/root elapsedは重複加算しない。短rootの時間比とcompile/実装検証費は別で、回収game数は算定していない。現在ピークRSSは各process receiptへ保存しcurrent空きや未来不在へ読み替えない。

失敗・未開始を保持: 最初のRust小数表記のformatter失敗、Cargo lock待ち中のforeignCPU guard停止14.3989秒（offender exactidentity未保存・UNKNOWN）、guardの`cargo`相対実行名SHA解決失敗（Popen前NN0/管理wall UNKNOWN）、旧monitor identity不在によるNOT_STARTED/0child、最終テストのmain cwd誤指定（対象なしでCargo exit101、0compile/test/NN、0.337245秒）。最後は私有cwdをchild前にassertする薄修復を行い、全元attempt/logを保存した。どれも科学性能の負例へ変換しない。

正frame22 loaded state・owned monitor receiptの現在PIDtick/config/contract/current24、実foreign CPU/計測process/RAM・承認済storageを各入口で確認。staleな11:59 running-loaded identityは新運用へ代用しなかった。LLM人数/owned非nullだけで拒否せず、他owner実計測と重ねない。runtime源や他owner源の変更/interrupt、本人Git/index/commitは0。

停止・再現・費の正本は[science-source-stop.json](../../research-data/ai-sigma/frame22-search-efficiency/science-source-stop.json)、[cost-and-attempts.json](../../research-data/ai-sigma/frame22-search-efficiency/cost-and-attempts.json)、各`process.json`/admission/preregister/config、最終源archive/member manifest。統合担当coordinatorが停止SHAを受け独立採用レビューとmainへの保存を判断する。最高目標は未達。
