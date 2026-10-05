# 172 native非劣性の費用と妥当な停止規則

2026-10-03、critic。契約1849f98998afc383fdb1d87054d5df1411a8baf7、親11。受領06:29:34.269455、ready/show goal+self、pauseなし・本人担当・169自域停止を確認し06:29:37.144498 claim/静的実開始。処理06:49:34.269455、新command06:46:34.269455、提出06:59:34.269455の早側を維持。新正式data/NN/game/Chrome/build/GPU/学習/委譲0。

**最大1採択推奨は、3arena等重みblockの固定lambda mixtureを使うNI専用の逐次検定である。** 5pp/片側95%は保持する。条件付きnullに対する停止規則は数学的に成立するが、stationaryなnative棋力の非劣性へ解釈するには、版・抽出分布・資源時計・条件付き平均の仮定が必要。現在は統計計画の条件付き支持であり、正式WDL開始/NI達成ではない。旧158固定m600式と旧165 W6L10を変更せず、旧成績をlambda/threshold/distribution選定に使わない。

## 選ぶ対象と観測単位

参照は固定Sigma-Web751186のnative-hosted JS、候補はfaithful Rust-native MCTS、同ONNX/native ORT CPU1thread。Sigma C++やbrowser NIの主張ではない。170保存bindingではbinary166dd0c4f5eef9cd02a189e9e8bb4811bd307f6545db83a07e7180ea410e96f8、modeld790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、ORT1.30 CPU/SEQUENTIAL/intra/inter1、private engine a78ea833、runtime bd7ffdeを示す。新正式manifestでは実行するsource/loader/binary/NN quota/探索設定・RuleA・clock・provider版をownerがWDL前に特定する。この読取は170のwholegameを再認証したものではない。

結果前補足によりcore[2,4,6]各1arena、block bに3つの独立fresh openingを割り付け、各openingを色交換2局でXi=(score1+score2)/2とする。goal勝1/負0/draw.5。Yb=(Xi2+Xi4+Xi6)/3、各core等重み。core8は不使用、CPU0の管理/監督1logicalを常時残し合計4logical以内。pair内依存、block内の機械競合・共有shockは許す。gameを6独立標本と扱わない。

主推定対象は、凍結した両engineと資源時計・新開始分布での期待pair scoreのcore等重み平均 μ=(μ2+μ4+μ6)/3。core別μcが違ってもよいが、各blockの条件付き期待Yが同じμであることを仮定する。独立block/定常条件は十分な想定で、数学上のe-processには全block独立より弱い条件付きnullで足りる。seed独立はscore独立/同じ条件付き平均を証明しない。host/time driftやcarryoverでこの仮定が崩れた時は、wealthが大きくても定常棋力NIを認定しない。core2 soloへの一般化やcore別NIは主対象外。

開始分布候補は12/13/24/25/36/37/48/49の長さを一様、各手pawn/wall class各.5、選ばれた非空class内の合法順を一様とする。class空時の処理も結果前固定が必要（空classを再drawして非空class内一様）。共有RuleA合法履歴で非終端、両距離≥3、距離差≤1、残壁各≥2を満たすproposalの最初を受理し最大256proposal。fresh entropyから独立slot seedを作り、seed導出/PRNG版・重複・色順を保存する。重複は保持し、勝敗で置換しない。色順はslotごと公平coinで決め、core割付はblockの固定順とし、core差を隠さない。生成上限失敗はGENERATION_UNKNOWNとして当該2局を[0,1]、成功inputへの補充0。

この抽出はAI結果なしでも実戦代表性や感度を保証しない。geometry条件は距離近似であり棋力均衡の条件ではない。旧診断/教師/候補選定と独立holdoutに分ける。生成失敗を含む品質scoreのlatent対象が定義できない場合は、識別区間は残せるが対象分布の成立は保留する。受理率や実生成を未測のまま『均衡/IID証明』にしない。全将来inputを先に検算する入口gateを増やさない。

## 検定と独立した短い証明

θ=.45、Λ+={1/4,1/2,1,3/2,2}、各初期wealth1、重み1/5を固定する。

\[
M_n^\lambda=\prod_{b=1}^n[1+\lambda(Y_b-.45)],\quad E_n^+=\tfrac15\sum_{\lambda\in\Lambda_+}M_n^\lambda.
\]

H0+は各bで E[Yb|F(b−1)]≤.45。全Y∈[0,1]、λ≤2<1/.45より因子最小.1、最大2.1で非負。M(n−1)は過去可測だから、

\[
E[M_n^\lambda|F_{n-1}]=M_{n-1}^\lambda\{1+\lambda(E[Y_n|F_{n-1}]-.45)\}\le M_{n-1}^\lambda.
\]

従って各M、等重み平均E+も初期1の非負supermartingale。VilleによりP(H0+の下でいずれかのnでE+≥20)≤1/20=.05。最大n200や硬期限・資源停止を加えても、false NIの確率を増やさない。これは検出力や期限内達成の保証ではない。

この構成の一次根拠は[Waudby-Smith/Ramdas v7 §4, Proposition2–3と§2.2 Theorem1](https://arxiv.org/html/2010.09686v7#S4)。非負capital processとVilleの関係を参照し、今回の固定5点mix/片側複合null/未知範囲の証明は上の独自算術で行った。70頁読了や文献総覧をgateにしていない。

共通conditionalmean μを仮定するとH0+はμ≤.45となり、棄却はμ>.45、すなわち実用許容5ppのnative非劣性支持。厳密な両側等価/μ≥.5/世界最強ではない。条件付き平均がblockごと異なる場合、棄却できるのは『全blockの条件付き平均≤.45』という仮説であり、定常μのNIへ読み替えられない。

反例: Z~Bernoulli(.45)を一度だけdrawし、全Yb=Zとする。各周辺平均は.45だが、Z=1なら6blockで閾値に達し、支持確率.45となる。2block以降の条件付き平均はZなのでH0+を満たさない。fresh opening seed、共通searchseed、周辺平均の一致だけではこの問題を排除できない。

停止後に通常の固定n 95%CIを付けることはしない。閾値判定はその一点の片側検定であり、score精度.05や数値的CI下限の値を返すものではない。必要なら『棄却時(.45,1]、非棄却時[0,1]』という粗い片側confidence setは上のcoverageから説明できるが、平均±誤差のCIとは別。より精細なCSにはmごと非負性を保つfamilyを事前定義して反転する必要があり、今回の追加案にはしない。

## 未知scoreと容量/観測列の区別

品質scoreは正常で合法な終局なら点値、未実施/infra/reference fault/clockunknown/候補faultは[0,1]。候補faultの**運用**score0は別欄に記録し、品質の真の敗北と混同しない。参照faultを勝利1と補完しない。block6gameの下端/上端をそれぞれ等重み平均してYlow/Yhighとする。正常drawは.5、局間・pair内依存を維持する。

全λ+の因子はYについて単調増加・非負。従って全unknownの真値を許容範囲内のどこへ補完しても、E+(Ylow)≤E+(Ytrue)。下端wealthの閾値到達事象はtrue wealthの到達事象の部分集合なので、欠測が結果に依存しても保守NIを支える。ただしlatent品質対象とconditionalnullの成立を仮定する点は残る。欠測をexclude、complete-onlyや成功補充に変えていない。

台帳とwealthを次のように分ける。

1. 最大capacityは200block/600pair/1200game。全slot IDとcore・状況・停止理由を持つが、capacityの事前宣言や将来seedの計画は、blockが観測列へ入ったことではない。
2. 各blockのattempt登録は最初のlaunch前に行う。登録済みblockは未開始でもUNKNOWNとしてlow/highを持ち、開始済み/一部未完了も同様。block順に全3pairの結果またはtyped未知を確定して一度だけ取り込む。飛越し・速勝先取り・中途gameごとのwealth判定0。
3. 一度に1blockだけをadmitし、3arenaを並行、その後のblock barrierで判定する。NI閾値後は新blockをadmitしない。予備生成されたcapacity slotでも、未admitのfutureはSTOPPED_BY_VALID_RULEとしてwealthへ0を追加しない。既admitのblockを事後にfuture扱いして除外しない。
4. harddeadline/resource/pauseでは現在登録blockを待てる範囲で回収し、未完了をUNKNOWNにして順序通り取り込む。支持閾値未到達なら不確か/実測不足。科学条件のclock/source/resource違反が判明したらCLOCK_UNSETTLED/PLAN_UNSETTLEDを別に立て、wealthだけで救済しない。

処理prefix nの主統計はE_n^+(Ylow)、補助記述はprefix低高平均ΣYlow/n〜ΣYhigh/n。maximum200全slotの未観測を[0,1]とする記述的識別区間は、ΣYlow/200〜(ΣYhigh+200−n)/200（admit済み未完了はprefixの未知内に含める）。後者は有限capacityに想定した全slot scoreの範囲であり、逐次検定の分布期待μとは別の対象。例: 一定Y=.5が44blockで止まるとNIは支持候補、capacity低高は[.11,.89]。未知幅が広いことと、モデル仮定下のμに対する逐次推論は矛盾しない。600pairを完了した扱いにはしない。

complete-onlyの平均/WDLは補助、全attempt品質/運用/fault台帳を維持する。旧固定m600式へこの停止を後付けしない。

## 数値判定と小mock

6game scoreの半点単位合計k∈{0,…,12}によりY=k/12。λ=a/4、a∈{1,2,4,6,8}なら因子は[240+a(5k−27)]/240。prod整数を5本維持し、exactにΣprod≥100×240^nならNI。200blockの整数は小さく、外部数値依存なし。logsumexpは副表示に限定する。float表示が20近傍でもexactで確定できなければNUMERIC_UNKNOWN、支持を返さない。原thresholdを数値epsilonで緩めない。

check-r1はextreme/未知/latent反例/将来ゼロpaddingの誤り/score変換/logsumexpとexact整合を小さい人工列で確認した。実AIデータ、Monte Carlo power、NN実行は0。

| 人工列 | NI最初のblock | 実行game換算 |
| --- | ---: | ---: |
| 全Y=0 | 200までなし | capacity1200 |
| 全Y=.5 | 44 | 264 |
| 全Y=1 | 6 | 36 |

これらは分散0の例で、真平均.5の通過powerではない。追加のIID Xi~Bernoulli(p)、Y=Binomial(3,p)/3という仮定例での200block expected log（最も大きいcomponent）はp=.5:2.90786/λ.5、p=.55:11.41522/λ1、p=.60:24.83537/λ1.5。λをこの計算で選び直さず全5点mixを維持する。mixの1/5 penaltyを隠さず、期待logもpower/期待停止時間ではない。p=.5の一component logはlog20≈2.99573より小さく、高powerを約束できない。旧600pairをmean.5で通すHoeffding境界と、逐次検定のcapacity/powerは別である。

劣性方向が必要な場合の**非採択の補助仕様**: Λ−={.25,.5,1,1.5}でE−=mean product[1−λ(Y−.45)]、H0−:conditionalmean≥.45、Yhighの保守wealth≥20でμ<.45支持。因子最小.175、非負/減少なので同じ証明が使える。別片側5%であり、NIと劣性の両方向を同時95%とは呼べない（両方向誤判断のunion上限10%）。本推奨はNI-only stopで、劣性停止を入れるなら最初の正式data前にenabled/規則を固定する。結果を見て有効化しない。

## 費用、成立分類と次の登録判断

旧native16管理job431.553877秒は費用例のみ（旧取消tailを含む）、平均26.972117秒/game。1200solo8.990706h、理想3parallel2.996902h。2色pairを各coreで順次行う理想block53.944235秒、一定Y=.5人工44blockなら約39.56分だが、これは実際の棋力/停止時刻/新mode費の予測保証ではない。200ply×500ms=100秒/gameの思考部分上限では1200の理想3parallelでも11.1111h、開始/cleanup/保存等は別。

170の40要求はactualend402/public500/両zero後nextt0、4arena pool2/4/6/8/RAM約1.686GBの有限支持。core2のsolo対parallel steady/完成量減少があり、4parallelのwholegame倍率を推定しない。新3arena wholegame費は未測。受領時親残6346.731秒（1h45m46.731）、重開始停止08:05:21/終了08:15:21を維持。capacity600pair完了保証0。CPU0の管理/監督とRAM8GiB内current+forecastをownerがadmitし、同じ3modeで最初の正式blockをそのまま取り込み、診断成功選別で廃棄しない。

分類は次を分ける。

- **統計計画成立候補**: 上のproof、固定λ/threshold/capacity/unknown/順序を結果前採択。
- **PLAN/CLOCK_UNSETTLED**: 正式版/provider/抽出分布・latent対象/時計/資源modeが未固定または不成立。e-valueで条件を救済しない。
- **NI_SUPPORT**: 固定条件下、prefix lower wealth≥20かつ科学条件の未解決によるscope失効がない。実用5pp片側95%のnative主張のみ。
- **UNCERTAIN/INSUFFICIENT**: capacity/硬期限/資源に達しても閾値なし。支持なしを劣性支持へ変換しない。
- **劣性支持**: 上の補助方向を結果前に別採択した場合だけ。現在のNI-only案にはその結論を含めない。

kernel CPUのexact同値、全host/全期間保証は求めず、allowed resources・同じwall配送/actualadmit・原因側cleanupの必要な有限証拠を使う。ただし170短要求でwholegameと未測kernelCPUを解消した扱いにはしない。統計案の受入れとformal readyは別。追加の全役承認・全deep/root/hash検査・全paper待ちを新gateにしない。新formal dataを出す前にcoordinatorがscience adoptionとmanifestを固定する。

## 保存と自域停止

writerはresearch-data/ai-sigma/172-native-ni-efficient/と本報告のみ、170/旧comparison protocol/原計画はreadonly。新sourceは同data域のcheck.py/managed.py、結果・smallmock・primary参照・入力計画を保存。CPU0単1、check-r1 .387394秒・親子sampleRSS32,354,304B<guard896MiB、wait完了・currentidentity不在。瞬間peakや全hostの証明ではない。static/管理180秒、先行20秒保守計上。保存直前current+新2MiB forecast93,932,678B<critic112MiBguard、旧未知減額/親追加予約0。必要Git stream復元、source/子停止、Beadsnotes/backupと最終配送はhandoffを参照。受入れ/closeはcoordinator、goal/他者close0。
