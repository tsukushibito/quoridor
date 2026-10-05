# 295 凍結済み公開/RuleA zの保存算術

旧291の凍結予測を新NN0 jobで一意joinした。モデル、candidate49dbc1ec/weights213309、evalfreeze8e842b0b、両mask、Tseen67937+ALLrawV19965、D(0,8)およびtrain-only定数は変更していない。定数0.005460941754861121は実Tseenの67937個±1から独自平均を再計算して一致した。status=goalとterminal_reason=GOALを別フィールドとして検査し、勝者と保存absoluteSTM側から終局zを独自算術で照合した。親producerの共有RuleA合法終局資格・inputreaderに依存する有限照合であり、全teachertruthではない。

公開0043: 全19359行/10入力群、OR除外15770、inputeligible3589/2群、理由不明z0をさらに2行除外し最終3587行/2群、8zeroeligible。全rawz0=23は終局理由欠測として保存する。group-equal MSEは候補1.1123810069464133、D1.0、定数0.9999540184844627。row MSEは候補1.1112936094759978、D1.0、定数0.9999658799964461。候補sign0.50347、Dsign0.0（D=0に対し±1の符号完全一致定義）、定数sign0.50347。公開game/history/絶対P2/終局理由は不明、同入力反復群を独立gameと見なさずgame CIはUNDEFINED。適格inputとrecorded±1に条件付けた結果であり公開全gameやdraw期待結果へ一般化しない。

別RuleA48: 全48family/1668行、OR除外0/zeroeligible0、actualGOAL48/draw0game0。family-equal MSEは候補1.502603045872717、D0.6148462922582846、定数0.9997993224224874。候補−Dは+0.8877567536144327、固定fit家系paired2000/seed29180311の95%区間[0.5922742789722851,1.2006278978242453]、12改善36悪化。符号完全一致率は候補0.5404780605、D0.8002633172、差−0.2597852567、95%区間[−0.3635880965,−0.1621854863]。候補の飽和(|p|>=.99)家系平均0.190908573、D0。row MSE候補1.459901166、D0.668682398。cohort/side/plyphase/calibration/perfamilyを圧縮全結果へ保存した。

この有限分布では凍結公開z候補の予測転移/昇格を支持しない。48固定cohort/開始位置/family相関があり普遍IID精度ではなく、αβ同時間棋力を測っていない。Native照合済み5257予測と24witness/72nativeを再評価せず、同保存値だけを使用した。公開provenance/履歴欠測、教師noise、分布差、残差過信の単独原因は特定しない。旧291のschema assert失敗/MAX2/UNKNOWN+upper0/NOT_RUNは原保存のまま、旧287/293等とも別の新結果である。

次最大1案: Dを維持した残差振幅の正則化をtrain/selectionだけで固定する低費用単一対照。残差飽和/転移不足を制約する判別であり、公開教師不良の一意原因診断とは呼ばない。今回評価を設定選定/補充へ戻さず、今scopeでは新fit/forward/教師/対局を開始しない。最高棋力goal未達。
