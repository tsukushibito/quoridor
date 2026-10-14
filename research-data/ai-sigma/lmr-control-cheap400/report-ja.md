# LMRとCheapの有限評価結果

元96探索／48sessionsと元128局／64色pairを、同じ真正image66c0daac／Buildde4a7995で一度ずつ実行した。探索は94COMPLETE＋固定D Control OFFのtargetD6UNKNOWN2、対局は128goal／UNKNOWN0。6765手が受理され、fallback/error/forfeit/lateは0。元のFAILEDと真正未入場suffixの別continuationを保存した。

研究判断は、検証済みLMRを既定OFFの任意設定として保持し、LMR ONまたはCheapの一律昇格は保留とする。有限費用低下は支持されるが、同時間の棋力優位・非劣性は確立していない。製品／実generatorの既定、モデル、paused学習には反映しない。

| 評価器／ordering | LMR OFF whole秒 | ON whole秒 |   ON/OFF |
| ---------------- | --------------: | ---------: | -------: |
| nnue4k-control   |        7.757735 |   2.339680 | 0.301593 |
| nnue4k-cheap     |       17.103007 |   3.339701 | 0.195270 |
| fixedD1M-control |        3.121735 |   1.153453 | 0.369491 |
| fixedD1M-cheap   |       12.877199 |   2.476077 | 0.192284 |

wholeは各6roots＋setup/drop・採点・cache等込み、OFF→ON→ON→OFFの各条件2回中央値。NNUE TT4096、固定D TT1048576、通常diagnostics/depthcallback OFF。ONは選択的探索で値・PV・workが変わるため同仕事のspeedupではない。固定D Control OFFはD5完了後8M上限、Cheap OFFは全幅D6完成、ONは両者で名目D6完成。古い392のdepth別UNKNOWNへ遡及しない。Cheapの絶対wholeは両evaluator・LMR条件でControlより大きい。

| 評価器   | 左対右                    | 左の勝-分-負 | 保存family95%範囲 |
| -------- | ------------------------- | -----------: | ----------------- |
| nnue     | control OFF 対 control ON |        8-0-8 | [0.25, 0.75]      |
| nnue     | cheap OFF 対 cheap ON     |       10-0-6 | [0.375, 0.875]    |
| nnue     | control OFF 対 cheap OFF  |       14-0-2 | [0.625, 1.0]      |
| nnue     | control ON 対 cheap ON    |       10-0-6 | [0.375, 0.8125]   |
| distance | control OFF 対 control ON |        7-0-9 | [0.25, 0.625]     |
| distance | cheap OFF 対 cheap ON     |        9-0-7 | [0.375, 0.75]     |
| distance | control OFF 対 cheap OFF  |       10-0-6 | [0.3125, 0.875]   |
| distance | control ON 対 cheap ON    |       5-0-11 | [0.125, 0.4375]   |

全対照で同じ8family×2色、100ms authority receipt／5ms reserve／depth64／node安全上限1M／200ply、AI2/6＋main4。区間は原native family bootstrap引用のみ、追加bootstrap0。共有family・多重対照・固定bookへの条件付き観測で、128独立標本や正式棋力認定ではない。

NNUEはControl OFF対Cheap OFFで14勝2敗、LMR ON同士10勝6敗だった。LMR自体のControl対照8勝8敗では強さ向上を判断できない。固定DはControl ON対Cheap ONでCheap11勝5敗だが、Control OFF対Cheap ONの直接対照は無く、間接的な勝敗を足して4条件の首位を決めない。NNUEの利益を固定Dへ移植しない。

LMRは名目完成深さを上げる傾向があるが、その深さを全幅minimax保証にしない。6765手のterminal workだけを加算し、内包されるselected snapshot／persistent TT viewは別に保持する。reserveでstopcancelledの14手はいずれも完成snapshot＋reserve_stop_is_not_user_cancelで、ユーザー取消や失敗局ではない。全検索時間・物理NN呼出し・孤立したmap/採点/LMR費・continuous RSS peakはUNKNOWN。

数値jobの非重複outer費は964.170029259s、必要software Build v1..v6の非重複outer費は240.259264835s。原失敗を含み、native/guardian/sequenceのnested時間は加えない。source/LLM/通常修復/adminの全時間はUNKNOWN、個別receiptを保持する。保存解析費はそれぞれのguard receiptで別記する。

元72探索＋真正未入場24探索、元16局の別保存検証＋真正未入場112局を区別した。原cost96-v2・first16のFAILED manifest、初期source/fixture/consumer/入場前拒否・元RAW／費／returnedとpersisted masksは変更しない。6stage softwareの17新Rust＋影響3、7新Python NN0の実成功scopeと限定source/O1/consumer reviewを再用し、旧成功suiteを再演していない。

設定・原結果・source/修復・software/review・各詳細報告と原FAILED／STOPは[保存receipt](receipt.json)とexact archiveに保持する。追加trial／root／cap／parameter sweep／sampling／生成／fitは発行しない。混合・learnerの全準備／pipelineと323 USERPAUSE、defaults/models/seals/oldfits96を維持する。
