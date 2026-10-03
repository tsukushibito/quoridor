# 現CPUブラウザのbaseline差を測る設計

quoridor-4lc.147 / 枠10 / 2026-10-03。候補Q0/C1.5と固定Sigmaの現在の差は未測定であり、旧119のW4L12を今回の弱さの前提にしない。最大32pair・64gameの探索的対局を支持する。ただし測れるのは結果前に固定した生成分布と現在の時計・資源条件の差であり、小さい差や正式NIを認定できる標本ではない。採択・実行はcoordinatorで、149の静的準備を本報告待ちにしない。147の新NN/Chrome/model/game/buildはすべて0。

## 最大1案

新しいlegalprefixを4/5/12/13ply各8個、合計32個に固定し、同じ履歴をcandidateの色1・色2で一度ずつ対局する。盤面を反転して別履歴を作る操作ではなく、同じstate/historyでengineの色を交換する。各層で開始手番はそれぞれP1/P2/P1/P2となる。4層を等重みとし、各pairの `Xi=(色1score+色2score)/2` を単位にする。勝1、RuleAのgoal優先後の200ply draw .5、正常敗北0。64game・手数・seed反復を独立64位置へ数えない。

生成は既119のAIなし方式を使用する。初期局面から各手、両クラスが非空ならpawn/wallを各1/2で選び、そのクラスの固有合法順から一様に選ぶ。空クラスは他方を使用する。全合法手から一様に選ぶ方式との混用は避ける。生成seed一覧・PRNGのビット演算・attempt導出・履歴/side/key・合法順・非終端条件・上限を実験前登録する。新seed一覧は148/統括が固定し、旧119入力は採用しない。各slotは先着合法非終端履歴を採用、最大100生成attempt、枯渇は未生成として残す。全候補attemptと理由を保持し、勝敗を見て追加しない。

exact history重複もtrueState合流も事前記録し、後者を結果後に置換しない。原則として重複を勝手に拒否する条件付き分布を増やさず、同stateでも履歴が異なることと独立coverageの限界を示す。先着採用・非終端条件・attempt上限を含む生成器の出力が対象分布である。seedstream分離だけで確率的独立を証明したとは呼ばない。

policy/model/ORTCPU1thread/CPU[2]、候補caps・精度・order・tie・finish、固定Sigma条件を固定する。T500/cutoff402/adopt411/searchseed1979を保持し、serialized requestとreceiptで一致を確認する。seed一致は同じ探索乱数経路を保証しない。32pairを4層巡回の8roundで進め、各層で先に行うcandidate色を交互にして各4pairずつにする。層順もroundごとに巡回する。順を結果前登録し、完了群から都合のよい順へ変更しない。

## 分布と感度の限界

この生成器は合法性を保証するためのもの。均衡局面、通常の人間/AIの中盤、IID、一般棋力の代表標本を保証しない。pawn/wallクラスを均等にすることも研究者が選んだ分布の一部であり、残壁・距離・側優位を偏らせ得る。色交換はengineへの色配分をそろえるが、同じ側がほぼ確勝の状態を中立化しない。両色とも同じ側が勝つpair、真draw、candidateが両色勝つ/負けるpairを別に記述する。前者のXi=.5を「互角局面」や「engine同等」へ変換しない。

同モデルのroot priorだけでも結果が固定される局面を、AIなし合法生成だけで完全に避ける定義は得られない。この不足を隠さない。今回の分布は上記生成器として定義し、prior/value/root1/勝敗に基づく入力選別を導入しない。実gameに既にある初根のprior集中・採用Action一致と、両色同側winner率を事後の記述に使えるが、その後の標本追加や結果の除外には使わない。全結果が同じでも今回差を検出しなかったことまでで、小改修感度や差の不存在は認定しない。旧壁なし144のroot1全winはこの点の反例であり、一般対局の差を先取りする根拠ではない。

旧119の保存16gameは独自にwinner/色から再算し、8pairのXiは `[0,0,0,.5,.5,.5,0,.5]`、平均.25、W4L12だった。これは旧生成・版・時刻条件の記述である。145の3prefix×色×2variantの12局案は旧結果後に選んだ3位置の提案で、新独立12位置ではない。旧3fixture×2searchseedも独立6位置に扱わない。旧116の正式設計・成績・期限を更新しない。

## 結果前に固定する精度と欠測

主記述は、予定32pairの固定集合平均と4層別・色別・全attempt。探索的区間法を両側bounded-pair Hoeffdingに一本化する。独立な `[0,1]` pairの条件付き期待値について、`r=sqrt(log(2/.05)/(2*32))=.2400806978`、全完了なら `[max(0,mean-r),min(1,mean+r)]` とする。4層各8の等重みでは各pair重み1/32なので、層の分布が異なっても同じ独立bounded式を使える。これは独立性が成立するモデル上の区間であり、PRNG seedや共有環境・時間driftの独立性をこの設計で実証したものではない。固定32件そのものの平均にはサンプリング誤差はなく、区間は生成分布への一般化の仮定を追加した表示である。

旧116の片側幅約.216と今回両側幅.240を混同しない。64game独立扱いによる±.1698は使用しない。同じ式の±.05には738pairを要し、今回の32pairで近傍同等性や所定powerを保証しない。層別8pairの幅は±.4802程度なので、層のbest結果だけの主張や層別有意差認定はしない。区間が.5を含めば差の有無/規模は不確か、含まなくても支持はこの分布・運用に限定する。

未知game scoreは `[0,1]` とし、既知scoreの和をS、未知slot数をUとして、予定64gameの固定集合平均の識別区間は `[S/64,(S+U)/64]`。片色だけ完了したpairも既知半分を利用できる。主32pairを完了pair数で縮めない。この区間の両端をrで広げた表示は、独立bounded仮定下で全予定集合の期待値への保守表示にできるが、欠測理由や時間相関を解消しない。未知半数・残り全勝なら [.5,1]、全負なら [0,.5]、全未知なら [0,1]。complete-only平均は補助記述に限定する。

goal/drawのterminal品質、candidate責任faultによる運用loss、reference fault、shared/unknown infra、未完了、未開始を分ける。candidate faultの運用score0を純terminal品質へ混ぜない。reference faultをcandidateの棋力勝利へ換算せず、主品質はunscored。engine責任の対称な運用規則を別表に固定し、そのscoreと主品質の分母を明記する。browser/審判/encoding/時計/所有不明はengine lossにしない。純品質の識別区間ではfaultを未知として含める。科学gameの成功置換や再戦補充0。修正が必要な版は旧attemptと区別し、同一成績集合へ無断で統合しない。

停止は固定32pair終了、又は登録wall/resource/deadline/pause/回収不能。途中WDLによる早期成功/敗北停止や数の拡張0。安全停止の欠測は残し、固定終点が満たされなかったことを明示する。中間速報は停止・運用状態の報告で、最終区間を何度も成功判定に使わない。

## 同wallと推論量

主要比較は現在のready-relative T500運用である。input_available→own_wait→dispatch t0→API→最初/採用CP→合法clone/UTF8→t1→旧discard/ACKを分ける。自己回収後t0なら「入力供給から500ms」へ言い換えず、自己待ち・残処理・対局wallも別に示す。採用Action/sequenceの不変、確定後新NNなし、自己旧zero、相手t0は旧ACK非前提という必要機構を保つ。API awaitやACK wallをkernel CPUへ代用しない。新評価のために全期間CPU証明を一律入口条件にしないが、正式等CPU認定は保留する。

startup、手NN開始/完了、採用CPのNN、completed backup、terminal-noNN、root展開、discard、capsを別分母でengine別に報告する。旧119の採用CP-NN中央値8対10も当時の量の記述であり、今回の量差や原因を先取りしない。同completedは同NN/CPUではない。異なる対局軌跡のNN総数比は、局面・手数・terminal差を含むので速度原因の比較に使わない。同inputの両色gameに既にある初根で量と初回CPを対応させ、全手の分布も残す。

量が著しく違ってもsamewall結果を量の近い手だけへ選別しない。事前補助フラグは同input初根の採用CP-NN中央値比が1.5以上（または逆数が1.5以上）、zero/欠測は比を算出せず別件数とする。これは機構調査の優先度フラグで、統計閾値や因果判定ではない。samecompleted全対局を追加すれば主要運用を変更し、最大64gameをほぼ倍にする費用が生じるため今回の自動追加は不支持。必要なら次配分で、結果を見て有利な位置を選ばず固定同input/Kの対照を行う案を検討する。これは最大1案に付随する後続判断であり、新実行許可ではない。

## 費用と裁定

4層各16game、global200plyからprefixを引いた最大新手数の名目T500配賦は6128秒。149のbrowser7200秒に対し残り1072秒で初期化・startup・自己待ち・終了保存などを収める必要がある。これはwall完了保証でなく、実overheadが大きければ未完了となる。各game fresh session/startup6なら64gameでstartup384を手NNへ加算しない。追加samecompleted gameは0。

設計は有限な大きいgapを確認する入口として支持、小さいgap/代表性/純CPU因果/正式NIへの使用は不支持。最大1案は上記層化32pairの固定分布・全attempt・欠測区間・samewall比較である。係数変更145を今測るよりも、未測定のbaselineを先に測る配分に情報価値がある。結果が近い/不確かなら未検出を残し、今回だけで政策変更やSigma達成を宣言しない。

## 保存と実行

契約/選定Git40243b25804f8e929a6af5680c02a2b70bef39d1。本人00:27:40UTC受領、00:28:06claim。早側処理00:47:40・提出00:52:40、親04:15:21終了を維持。開始報告と10分以内の速報はApp Serverに受理されたが、科学採択とは別。独自静的算術は `tools/ai-sigma-frame10-gap-design/check.py`、原checkerをimportしない。CPU0単logical、448MiB guard、各60秒/管理180秒。全attempt/log/command/前後source hash/必要入力Git-SHAは `research-data/ai-sigma/frame10-gap-design/`。詳細停止・資源・復元は同域の最終manifest参照。過去未確認量の減額・親追加予約0。原成果/shared/model/parent/role/defaultindex編集0、受入れcoordinator、goal/他者close0。
