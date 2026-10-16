# 同一7状態の直接静的評価（422、2026-10-16）

結果前に固定した419の3親と4 endpointを、完全prefixから同じcoreで再生し、実手番STMで直接評価した。Search・depth0探索・MCTS・対局・fitは行っていない。対象は同じ2対局の親子を含み、4葉は419で単一置換が候補選択へ影響したものを選んだ集合である。7個の独立な無作為標本ではない。

| 同一状態              | STM | 残壁 P0/P1 | NNUE pre-tanh | NNUE post | Sigma raw/adapter |         D |
| --------------------- | --- | ---------- | ------------: | --------: | ----------------: | --------: |
| slot4 / ply11 親      | P1  | 6/8        |     +1.579391 | +0.918507 |         -0.005028 | -0.099668 |
| slot4 / ply39 親      | P1  | 0/2        |     +4.482471 | +0.999744 |         -0.989549 | -0.833655 |
| slot5 / ply12 親      | P0  | 8/8        |     +1.574982 | +0.917815 |         -0.511228 | -0.099668 |
| slot4/11 + [156,91]   | P1  | 5/7        |     +1.277223 | +0.855743 |         +0.106743 | -0.291313 |
| slot4/11 + [156,196]  | P1  | 5/7        |     +1.427306 | +0.891113 |         -0.579440 | -0.462117 |
| slot4/39 + [192,43]   | P1  | 0/1        |     +5.273468 | +0.999947 |         -0.986520 | -0.800499 |
| slot4/39 + [60,53,61] | P0  | 0/2        |     -4.075870 | -0.999424 |         +0.997868 | +0.800499 |

BEST43はfresh353のweights046fe926 / descriptor46ec2c47 / evaluator96a5f41f。標準化distance入力・FT32/H32/QF1/Zero4・output bypass OFF・Scalar FTを維持した。pre/postは正本headの一回の計算から取得した。Sigmaはd790dac6、CPU ORT library c902c70b、FP32/batch1/intra1/inter1、既存runtime factoryを使用した。policyは使わないが、policy/valueを一緒に計算する費用を含む。Dは同じDistanceEvaluator(0,8,tanh)である。すべて非終端で、親状態は不変だった。原prefix、HistoryKey/全履歴counts、壁、在庫、特徴bits、実image/モデル参照は[input.json](input.json)と[result.json](result.json)に残した。

Sigma rawとadapterは無変換で返す同一forwardの値として記録している。二つの独立な出力観測によるparityではなく、現役adapter sourceとの対応である。モデル/libraryのbyte同一性と既存CPU参照を再用し、5状態referenceや旧成功suiteを再演していない。ORT1.30.0は既存metadataで、新たなruntime version queryは行っていない。

親3状態の旧値は探索値なので、旧「直接値」との差はUNKNOWNとする。4葉では、NNUE pre/postおよびDの直接値が419の保存値とbits単位で一致し、差はすべて0だった。旧full/delta/undoの有限parityを再用し、追加delta/parity呼出しは0である。

この表で最も大きい食い違いの一つはslot4/ply39で、同じP1視点のNNUE +0.999744に対しSigma -0.989549、D -0.833655となった。NNUEの正本pre-tanhは+4.482471であり、root探索値を静的NN出力へ読み替えた数値ではない。葉[60,53,61]も、実手番P0でNNUE -0.999424、Sigma +0.997868、D +0.800499となる。一方[156,91]はNNUEとSigmaが正、Dは負である。

確認した入力・STM・尺度・保存値との対応では、明確な座標変換や符号反転の不一致は見つからなかった。実モデル間の同一状態の関数出力が異なることは観測できたが、Sigma/Dの同意を最適WDLや正解とはしない。飽和、旧対局の敗因、NNUEの弱さの単独原因、一般相関や棋力改善はこの7状態から確定しない。左右反転や単純な手番変更の厳密反転という未要求の性質も検査していない。

次は既許可421/423の独立したV family・残壁層・実対局で、新しいデータ/低反復と公開file順重みの実用差を優先して見る。今回の表の追加補充、全葉forward、再fitや新Searchは発行しない。公開fix43の生成各checkpointと現Sigma scratch321の学習史が同一だとは確認されていない、という418の限界を維持する。

## 実仕事・失敗・停止

実NNUE canonical headは7、full-context7、constructor head0、追加delta0。Sigmaはlogical/executed/physicalが各7、warm/failed/capture0、Dは7で、契約の28 head / 14 Sigma上限内だった。これらは物理FT/headハードウェア回数の認定ではない。Search/arena/fit/solver/bootstrapは0。

元direct7-v1はdescriptorのJSONキーをweights_shaとしたため、モデル数値入場前にFAILEDとなった。全head/Sigma/D評価0の原partial/log/費を保持し、正本weights_SHAへの1キー修復後、真正test-profileをcompile-onlyした。通常release bytesは修復前後b47014a3で同一だった。未入場の同じ7状態だけを一度評価し、成功した状態の再演や入力補充はない。保存collectorのstates対rows KeyErrorも原FAILEDのまま残し、保存metadataだけを訂正して収集した。

original job2c049937のouterは599.582022647秒、native guardianは598.516047351秒で内包のため合算しない。出力保存を含むwhole582.282537151秒とsetup/drop、Sigma内部同期時間0.033265083秒も合算しない。これはtest-profileの小さい記述診断で、速度比較ではない。途中のmetadata観測ではnative threadのp9_client_rpc待ちがあったが、全IO費の分解はUNKNOWNである。CPU2/別physical guardian4/family1GiB/GPU0/host reserve4GiB、NNP1を使用した。

native STOPは2026-10-16T01:38:03.048509Z。original child2965690/start16246607/boot6c2eはfresh absent、直接wait/reap、handles close、TMP削除とowned[]を確認した。saved collectionも別STOPで残した。連続family peak・全セッション費・actual global使用量はUNKNOWNで、原失敗のmask pending/record attemptedと後の正常cleanupを混同しない。旧342.17/323 USERPAUSE、models/weights/seals/oldfits96、製品/generator既定、foreign変更を保持する。

一回用のcfg(test) callerは結果保存後に現役sourceから撤去した。通常measurement本体は挿入前のbytesへ戻し、再構成元はGit 7cd6b405・元source packet・真正test-profile artifactとする。通常の評価器/factory/APIは維持し、既成功suiteの再演や新しい数値確認を行っていない。
