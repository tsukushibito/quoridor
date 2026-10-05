# 158 — Sigma初期同等の正式NI計画案

契約1・枠10、goal quoridor-4lc / 本人158。契約Git cd4aa34437457a2dd7d6bffd15b61f841fde57ff、受領観測03:05:55UTC、ready/show・本人割当・pauseなし・155 source/子wait停止を確認し03:06:47UTC claim。155のcloseはcoordinatorに残す。新NN/Chrome/model/build/game/学習/GPU/取得/委譲0。親終了04:15:21UTC、各停止時刻とCPU4/RAM8/保持＋予約12GiBを継承する。

判定：**第一統計案は条件付きで成立。正式開始は保留。** margin5pp、片側alpha=.05、固定600新pairを第一予算例として推奨する。抽出実装・独立性の扱い・凍結adapter版・時計/実効予算・159並列modeが未確定であり、統計式の成立だけで正式測定を開始しない。151/153/155は有限機構/診断の支持、Sigma初期同等未認定。NNUE最終目標を維持し、基準→自前PV環境/同等→NNUE＋αβの優先順位を今回拡張しない。

推定対象は「下記開始分布D、凍結した候補と固定Sigma-Web、指定browser/CPU同wall・同資源modeにおける期待pairscore μ」。候補色1/2の2gameを同じ開始state/historyから独立fresh treeで行い、goal勝1/負0/draw.5、Xi=(2色score)/2∈[0,1]とする。pair内依存は許す。個々のゲームを1200独立単位としない。native、GPU、他持ち時間、一般Quoridor全局面への主張は対象外。

候補政策は151忠実移植のC1/FPU.2/original-order/first tie/f64/根inclusive backup、Wasm SHA 500181795b373f69f6f2214ee1a77e12767e2f342e15a56ab5e27d0a0453f2c2を第一固定案とする。build/StageA b62cde0、StageB必要保存0e13191/f8444bddを区別する。参照はSigma-Web 751186344fc52ad0c29bc65922e62c6fa915f006、両者ONNX d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、ORT CPU/Wasm1thread・proxy false・GPU off・noise/先読みなし/temp0。新正式adapterのGit、全必要生成route/binary/model/provider、browser/ORT版、policy/caps/cancel・source manifestをWDL前に凍結する。151診断版を無記録で新adapterへ置換しない。

**最大1開始分布案D：幾何条件付き合法opening mixture。** 初期9×9/各10壁から長さLを12/13/24/25/36/37/48/49の8値より等確率に選ぶ。各plyは合法pawn／wallがともにあるならカテゴリを各1/2で選び、選んだカテゴリ内で合法手を一様選択する。一方のカテゴリが空なら他方へ確率1。wall内は向き/位置を合わせた全合法Actionから一様。履歴第三反復禁止を含むRuleAで逐次生成する。途中terminal、L末端terminal、両者いずれかの壁通行BFS距離<3、距離差絶対値>1、残壁どちらか<2ならopening proposal全体を棄却し、同じpair専用乱数列で新Lから生成し直す。飛越し・将来壁を含む勝利手数をBFS距離と同一視しない。

Dはこの生成法の幾何条件に条件付けた分布で、均衡・代表性・棋力感度を保証しない。長さや状態が受理される確率により、受理後の8長さは必ずしも等頻度ではない。結果後の層quota調整をしない。開始manifestには受理L/壁数/両距離/side/全history/keyを残し、対象範囲をこの法則に限定する。既4/5/12/13短openingの7/8pair同盤面側勝ちという診断を、より深い幾何条件を提案する理由として使うが、AIのvalue/prior/root1/勝敗で局面を受理しない。開始均衡の判定や全入力root1検査を追加gateにしない。重複状態/履歴はそのまま保持し、重複を削除して別分布にしない。

600pairの独立な新256bit OS entropy seedを、候補版凍結後・AI試験前に採取し、別domainのopening/search/color RNGへ派生する。generator/RNGアルゴリズムと拒否バイアスのない整数抽選、entropy provenance、全seed列、入力hashを固定保存する。color順はpair専用独立coinで1→2／2→1、pairの実行順位/core割当も別domainの結果なし乱数で固定し、長さ/sideが時間・coreに偏らない巡回配置を使う。共有searchseedを全pairに使わず、各gameで候補/参照には同じgame seedを供給してもpair間は新seedを使う。OS entropyの実独立性やCSPRNGを数学的IIDの証明としない。独立乱数源・fresh tree/session状態の隔離、時間drift/負荷の安定という実務上の独立性仮定を明記する。

各pair生成は最大256proposal。600入力をAI前に全て固定する。cap/例外で未生成なら計画のsampling実装が未成立として正式開始保留、得られたprefixだけへnを縮めない。生成済み部分のmanifestと未生成予定slotを残し、結果後の再生成/選別/良いopening置換は0。seedを都合よく追加して救済しない。旧119/145/149/151/153/155の入力・成績は正式holdoutへ混合せず、既診断署名と一致した重複があれば「新抽出で偶然出た重複」として保持・開示する。holdoutはモデル選定/学習/160教師exportへ渡さず、候補変更時は別の新認定計画とする。

第一案の半幅は e(m)=sqrt(log20/(2m))、全予定pairの低平均lowと高平均highから L=max(0,low−e)、U=min(1,high＋e)。品質主推定対象は双方が規約どおり完了した場合のcounterfactual terminal scoreで、欠測を[0,1]に残す。通常goal/drawはscore一点、候補に責任のあるtyped engine faultでも品質は[0,1]。運用副指標だけ候補faultを[0,0]にする。参照faultは両指標とも[0,1]で、無条件の候補勝1にしない。共有infra/時計条件不明/未開始/未完了/回収不能/原因不明は[0,1]。1色が既知で他色未知ならpair区間は2色区間の平均。全1200slot・m600は固定、complete-onlyは補助。faultが両engineにある場合はinfra/unknownを優先し、原因証拠なしに片側lossへ変換しない。運用NIだけで棋力NIを宣言しない。

品質L>.45なら本分布/凍結条件で5pp非劣性を支持。U<.45なら5ppを超える実用上劣性を支持。ほかは不確か。方向別の下限・上限は各片側95%であり、同時の両側95%帯ではない（union boundの同時被覆は少なくとも90%）。厳密両側等価の宣言は禁止。sampler/モデル版/資源clock条件が未成立なら統計値に先立って「計画未成立」、条件成立でも未測/未完了は「実測不足保留＋全予定識別区間」。全予定未知なら[low,high]=[0,1]、L0/U1。測定条件不成立を単なる棋力負けにしない。不可解なmissingnessでもlow≤実際の全予定平均≤highなので保守的な識別として扱い、complete-onlyのIIDを勝手に仮定しない。

固定n=600pair/1200slot、一度だけ最終判定。途中WDLによる成功/無益停止・n追加・方法変更0。pause・安全/回収・deadline/資源停止は別で、その時点の全予定未知区間を報告し勝ちで終了しない。NN開始後のgame再試行0、科学不成立も予定slotに残す。NN前launch障害は同slotで最大1の修復再試行を許す場合、その分類と旧attemptをWDL前に登録し、露出済み科学結果があるslotには適用しない。同じholderへ多数候補を試すと選定バイアスになるため、正式主候補は一つ。旧計画/旧rawを遡及変更しない。

| 固定pair数 | NIに必要なmean（厳密に超える） | mean=.5時のL |
| ---: | ---: | ---: |
| 100 | .5723873415 | .3776126585 |
| 200 | .5365409191 | .4134590809 |
| 600 | .4999644230 | .4500355770 |

重要な異論は費用/検出力の混同である。600pairは観測mean=.5なら通る最小級の例で、真μ=.5の高power保証ではない。600で分布自由power下限はμ=.5：約.00000152、μ=.55：約.950425、μ=.60：約.9999939。仮にXiがIID Bernoulli(μ)（pair内完全相関・drawなし）なら exact binomial power は約.516280/.993747/.99999970。Xi≡.5ならpower1なので、meanだけではpowerは決まらない。これは例示であり、実pairの引分・色依存をBernoulliに置換しない。

分布自由にpower≥qを保証する十分条件は、m>((sqrt(log20/2)+sqrt(log(1/(1−q))/2))/(μ−.45))²。q=.80/.90/.95に対しμ=.5は1800/2111/2397pair、μ=.55は450/528/600、μ=.60は200/235/267。欠測・条件不成立があればこれらのpower例より悪化する。第一案のm600は維持し、95%powerを予算条件にするなら正式WDL前に2397pairへ別計画として再見積もりする。別統計方式の提案は今回は0。bootstrap名目95%や結果後の効率方式変更で正式早期達成を作らない。

この下限とpower十分条件は独立・boundedの[Hoeffding原論文（1963、Theorem 2）](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf)に基づく。固定PRNG、各pairの共通環境、異なる時刻の熱/競合により独立性/同一μが崩れた場合にこの証明を適用しない。pair内依存はXiの範囲内で許容し、同じsessionの履歴cache/検索木を次pairへ持ち越さない。並列mode間の結果や旧単独と混合しない。

時計案はまず現研究adapter条件のnominalT500/cutoff402/adopt411を両者同じに凍結する。402はcache検証拒否条件、411は予定public採用、500は公開応答期限であり、実際には約411msまでの完成CPを使う比較である。純粋な500ms full-searchと同じ条件とは主張しない。atomic store/校正区間/CP合法採用/旧NN tailを分け、候補だけ早くsealする等を禁止。151に残るexact store/期間中drift/残kernelCPUの欠測があるので、正式公平性readyは現在false。

159へ必要な有限実証を提案する：同一core内の相手t0は通常旧ACK非前提を維持し、旧NNの開始/返却/停止・旧Workerの終了前CPUと新Worker overlapを原因側に帰属する記録または専用隔離方式を明示する。APIawait/sameKはCPU課金を代替しない。対戦engineを各専用coreで並列に隔離する方式を選ぶなら、1arenaで2logical使うことと通常1core adapterとの差を明記し、両engine同quota、全体4内で最大2arenaとする。新modeを無許可で実装せず、159測定/owner割当と実効予算方式を新WDL前にcoordinatorが固定する。時刻/残費が特定できないなら統計規則のみ固定し正式開始は保留、全host完全保証や全deep検査を追加gateにしない。

159の1core各solo→2arena→4arenaは計測条件/費用校正でありNI標本ではない。core2/4/6/8は物理別core候補、0&1/2&3は同coreという現情報をowner/affinity/性能/負荷で確認する。4modeはguardian/save等もpool4CPU内、他のCPU0計算脚本は停止または予定を分ける。4×1.85GB≃7.4GBだけでRAM8成立とみなさず、段階initと全owner aggregate current/RSS headroom/負荷を確認し、guard超過/不明なら2へ縮小または未実施。両engineが同程度遅化しても単独同条件としない。正式mode/core/barrier/session初期化/slot割当と計測許容差は159結果後かつ正式WDL前に凍結し、正式結果を見て速いmodeを選ばない。

費用例は旧診断353.880秒/16＝22.1175秒/局・53.5625公開手の有限参考を使う。600pair/1200gameの思考部分は単独7h22m21s、2並列3h41m10.5s、4並列1h50m35.25s。200ply×500msなら単独33h20m、2並列16h40m、4並列8h20m。初期化・warmup・保存・合法opening・回収/冷却・将来局面・drift分は別加算、速度維持を保証しない。μ=.5に95%powerを分布自由保証する2397pairは4794game、旧平均/4だけで約7h21m48s、最悪/4で33h17m30s。現在枠の残りから正式達成を約束せず、今回正式1200局も学習も開始0。

数値とschema/mockは自域calculate.py/numbers.jsonに保存。全未知・1色既知1色未知・候補fault/参照faultの分母と厳密境界を確認。03:08:35UTC、CPU0短い計算.000657秒、ru_maxrss約17MiB（瞬間peak完全保証ではない）、159heavy started記録なしを直前確認して実行した。全管理費はrun/通信/Git記録と分け、総120秒/各60秒/448MiB guardと旧未知を減額しないcurrent＋2MiB/critic112MiB guard内。必要停止/Git復元/backup後coordinatorへ引き渡し、root3docs/151/159/運用/default indexを編集しない。受入れcoordinator、goal/他者close0。
