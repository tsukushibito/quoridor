# 枠10 baseline対Sigma対局の結果前補足 / 149契約1
147criticと148hypothesisの独立速報を採用。今回は現candidateQ0/C1.5/immutable対fixedSigma/同model/T500/cutoff402/adopt411/searchseed1979を主比較とし、Cmatched145・samecompleted全対局・追加局所oracleを自動実行しない。候補の不足を前提にせず新分布の差の有無/規模を測る。

32slotは4/5/12/13ply各8、各slot色交換2game=64固定。seed/slot順/色順は research-data/ai-sigma/frame10-coordinator-start/adopted-seeds.json の32行を正本とし、全8attempt_seedsを使う（SHA a82f2d01875180aa6a4a53be6e62d1ae11b9ab01ef2b3d37e5a1b40a7ede5c04）。master61041のSHA256 domain混合推奨をそのまま採用、連番seedの初期class偏りを避ける。表のblock層巡回/色交互を保持、model/NN/AI結果を見てseed再選定0。

初期盤面からRuleA実合法履歴をbrowser main NN0で生成。両class非空時pawn/wallを1/2で選び、そのclassの既合法順から一様index、片class空なら非空だけ。xorshift32の最初classdrawとindexdrawの消費規約を既119生成器に合わせる。各slot最大8attemptの最初の合法非終端を採用。terminal途中/target、no-legal、不合法生成は生成拒否理由として記録。既119全8の入力signatureを結果に関係なく一律除外する。signatureは trueState key＋history_counts（キー順正規化）＋side のcanonical JSONとし、rootfeaturesを確認用に併記。WDLに依存するfilter、NN/prior/value/pathbalanceフィルタ0。新集合内の同じprefix/同じtrueState合流は保持してflag、重複による後補充0。最大8不成立slotは未生成の2game未知として保持。生成/全attempt/合法history/実Action/全32prefix文書hashと実sourceをAI load前に固定し、schema/admissionの安い検査後実対局へ進む。旧119の生成器のglobal duplicate rejectionは今回は無効化する。

32pair Xi=(候補色1score+色2score)/2、win1/draw.5/loss0、4層各8の等重み。全64予定slotを分母から落とさない。goal/draw、候補責任faultloss、参照責任fault、sharedinfra、unfinished/未開始/未生成の全attemptを別列。候補faultlossを含む運用scoreと双方terminal正常のみの手品質を分ける。参照fault/共有不明を棋力勝利へ変換せず未知score[0,1]。主平均は全予定scoreの識別区間 [sum known lower/64,sum known upper/64]、pair Xiの区間も同様。complete-only平均は補助としてm/選別限界を明記し主分母に置換しない。全pair同盤面側winnerを捨てず、両AI各勝のXi=.5と両色勝/両色敗/引分を区別。

探索的精度は独立bounded pair追加仮定の両側95%Hoeffding eps=sqrt(log(40)/(2*32))≈.24008を結果前固定。未知を含む主mean区間の両端へepsを外側に加え[0,1]へclipした参考区間を示す。固定PRNG/生成条件/共有state/時間drift等により独立性や被覆を今回立証したとは呼ばない。64game独立や全NNを標本数にしない。正式NI・一般通常対局・均衡/代表性を認定しない。

全32初期同入力の最初requestを両AIで対応させ、key/history/side/featuresとNN出力、採用CPのNN/completed、firstCP、待ち/旧NN残処理を必要最小に記録する。後続は異なる状態なのでNN総量比を機構因果や同仕事量にしない。startup別、API starts/完了/採用NN/terminal-noNN/discard/selfwait/ACKwall/cleanupを可能な保存分母で報告。モデル推論量が近いかは実分布を記述し同CPU証明へ変換0。samecompletedは別問いの将来候補のみ。

停止は固定32pair完了又は既契約の管理資源/絶対期限/回収不能。途中WDLで追加/停止/順変更/置換0。各job<=600秒、累計重7200秒の既予算内で実行groupsを予め登録、同model/2session保持・生成jobも重会計に含む。ゲーム成功行再実行0、安いglue修正は同課題内で旧失敗を保持し未開始条件だけ継続、全未来slotを維持。未完了は未知として返す。結果のmeanと.5との差はこの分布の有限差、参考区間が.5を跨ぐ場合は差未確定で現政策維持。跨がない差も一般棋力/NI認定ではなく次の実装改善又は独立新分布検証の優先に使う。全Xi.5なら同等認定せず尺度感度未確認。主結果と量の対応不足なら機構原因を保留し、弱さを前提に追加係数試験を始めない。

149本人の開始を確認済み。これはcoordinatorの結果前採択・実行補足でありroot146/92の事務受入れや147/148最終本文を新gateにしない。上限64game/既処理03:28:04.562204/新heavy03:18:04.562204/提出03:43:04.562204早側維持、親04:05:21/04:10:21/04:13:21/04:15:21UTCを延長0。元成果不変、研究scope/予算/政策の追加なし。
