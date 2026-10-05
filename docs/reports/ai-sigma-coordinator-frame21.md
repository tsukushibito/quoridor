# frame21: NNUE利益不足の原因と改善選定

実行枠は2026-10-05 08:37:54–10:37:54 UTC。目標は距離評価を上回るNNUEを作ること。今回、学習済み関数の探索接続、距離項を保持した学習と圧縮経路情報の増分、共通探索と教師推論の費用を分けて測った。最高棋力・未見局面での学習利益・Sigma同等性は未達。

## 得られた知見と選定

| 問い | 有限結果 | 採否・次判断 |
| --- | --- | --- |
| 学習した関数が探索に届かないか | 凍結228 Lと忠実step0 IのTorch/native・差分評価・視点対応成立。同16入力の完成depth1でL/Iの選択は異なる。node512/requested depth2はL14/16、I0/16、D13/16完成 | 一律の接続不成立という説明を狭める。正しい手や棋力の証明ではなく、値が枝刈り・仕事量へ与える違いを保持 |
| 明示経路情報を足すだけで利益が出るか | 同距離保持残差A/B、同初期・batch・5901 train/validation、400step。現Dのvalidation game-equal MSE .489403655、BEST200 A .478510425、DAG4付きB .478865629 | 今回の4値追加BEST利益を支持しない。T1/全map一括増量・幅/seed sweepは採らず、教師目標・局面分布・転移を次優先 |
| 適合の進展が転移するか | step400訓練誤差A .255723/B .231510に対しvalidation .524666/.529661へ悪化 | 最良200stepを保存。単に長くfitする案を優先せず、rootmean教師をminimax葉へ使う意味、戦略情報と分布を問い直す |
| 共通経路探索を速くできるか | u128層BFSは6tests、独立queue距離24624対応、合法21078 successor/親復帰。4prefix同仕事・53意味records一致。steady時間C:B D .071–.089、NNUE .131–.189 | coreをmain 79fc729へ採用。266旧版科学が停止した後の版として統合し、旧A/Bへ効果を移植しない |
| 同core改善が教師生成へ効くか | Sigma CPUORT K64 C:B .961–1.007で明確利益なし。4root排他profileでは推論API99.0858%、advance .2690%、supply .6049% | 教師生成の次候補は既存常駐GPU/真batch・active-game/pumpの稼働効率。同core短縮をMCTS倍率にしない |

QF1は二視点312疎入力と駒位置の距離2値で、全距離mapは入力していない。Sigma固定751186とClaustrophobia固定ae093653の一次sourceを参照した265は、距離場・pathmembership等と現在の情報を対応付けた。DAG4はそこから考えた圧縮仮説で、参照AIがこの4値を採用しているとは主張しない。距離2値があることと、有限教師・小モデルが戦略的経路を学習できることを区別する。

## 同時間比較の不足

266の結果前固定6多様opening×色交換、L対D/I対D全24予定は、各500000 NNの予算に達して全完了しなかった。終局1 LOSS、UNKNOWN2、NOT_STARTED21を保持し、学習の棋力利益を識別できたとはしない。途中結果による局面選別・成功補充・上限救済は実施しない。全対局を完了できる総NN費の見積不足と有効比較率は次評価の設計課題。

拮抗し多様なopeningを主層、偏った局面は別能力層とし、浅い強制勝敗・距離差・残壁・色交換を考慮する。Sigma値単独を均衡保証や閾値gateにしない。訓練には優勢・劣勢・終盤も必要で、評価用選定と訓練分布を同一にしない。旧173正式198は非学習、開封testは選定に戻していない。

## 次の改善方向

教師生成側ではCPUORTのfixed batch-oneモデルをAPIで束ねても内部は逐次実行である。現runnerは既にpendingをまとめるpumpを持つため、次は既存resident GPU/真batchバックエンドの実batch分布・待ち・同K/ID/root品質と有効教師/全job秒を結ぶ。推論APIの支配だけでGPU利益を確定しない。

学習側は距離保持Aを基準に、教師の戦略情報・分布とrootmean→葉利用の不一致を優先する。Aの低MSEを棋力へ直結せず、同入力・同完成horizonの行動と費を結ぶ次有限対照を検討する。経路4の負支持を経路情報一般の否定に広げない。追加研究は次の具体配分・資源と許可枠に従い、自動延長しない。

## 費用・運用・保存

個別科学wall: 267 8.680832秒/22748 NN、268 6.443924秒/221232 NN、266 A 3.652428秒/17016 NN・B 7.701121秒/1000000 NN、271 1.046819秒/256 NN。build/testは各報告で別計測。guardian/child/管理の境界が異なるため全CPU費へ単純加算しない。LLM・準備・一部管理の累積実費はUNKNOWN。

保管coverageと未使用cacheの整理に時間を要し、09:46の現物admission後に科学が進んだ。保持・必要forecast・未知128MiBを含む12,734,943,232Bが12GiB内という有限点証拠を使用した。旧欠測や予約を0へ割り引いていない。監督は期待JSON欠測、nested dependenciesによる保存cap拒否を各原失敗として保持し、有界selection修復後に実observe/finish/自己notes/backupへ到達した。

必要source・全attempt・結果・元失敗・回収・保存は各担当報告とframe21-coordinatorの受入れreceiptに接続する。1d2の旧worktree撤去・必要資産移行は別許可の保守であり、使用中入力は最後の自然読取停止まで保護する。

終了点検は92がheavy10:27:54、scheduler/正owned10:32:54、monitor10:35:54、保存10:37:54を所有。実終了証拠はその報告で確認する。この稿の作成時点では未来回収を完了認定しない。旧229 final NOT_RUN、旧失敗・未知・期限・成績、親最高目標未達は維持する。

参照: [265特徴選定](ai-sigma-hypothesis-frame21-feature-cause.md)、[267同仕事探索](ai-sigma-critic-frame21-search-efficiency.md)、268 managed WTのroute-control report/handoff、266 model-causeのscientific-stop-v1/compact/cost-ledger、271 managed WTのmcts-cost result/science-stop、[92運用・整理](ai-sigma-steward-frame21.md)。
