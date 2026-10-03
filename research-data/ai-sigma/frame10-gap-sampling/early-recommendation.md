目標quoridor-4lc/本文148、10分以内速報。推奨最大1案は新32prefix、ply4/5/12/13各8、各prefix候補色交換2局=64game。既119敗戦から選ぶことはせず、初期盤面→RuleA合法履歴、pawn/wall class各1/2（両非空時）・class内合法順一様を結果前に固定。生成seedはmaster61041からslot/attemptをSHA256 domain別にderive→browser xorshift32、最大8attempt/slot・最初の合法非終端を採用。既119全8入力signatureはWDLに関係なく一律除外を提案、新集合内の偶然重複は保持・flagし後補充0。別NN/value/balanceフィルタ0。seed表はrecommended-seeds.json、legal状態の実生成は今回0。

具体的偏り根拠：単純な隣接seed61001..61032はxorshift32初回class判定が32/32wallになった。hash混合表は18pawn/14wallで、その比率を見てseedを再選定していない。両者は小整数算術でありRuleA/NN/AI結果ではない。hash混合は独立/IIDの証明ではなく、連番seedの初期class偏りを避ける設計である。

8block各4ply層をhash固定順でinterleave。色順はblock偶奇で1→2/2→1、各層4ずつ。探索seedは通常1979を両engineで維持、C1.5/Q0/finish/order/f32/model固定。両AIで同側winnerのpairは捨てずXi=.5として残し、強い局面優位による感度低下を別解釈する。合法・層/色バランスは棋力上の均衡や実戦代表性を保証しない。

32prefixを単位にXi=(候補2色score)/2、4層等重みmeanを主尺度。64独立game/全手NNを標本数にしない。独立bounded slotという追加仮定なら片側95%Hoeffding幅.21635、両側95%幅.24008で、小差/NI.05は精密には測れない。実seed固定PRNG/層/反復/欠測からcoverageは未認定。分母32/64固定、失敗・同側winner・未生成・未開始を保持し、勝敗を見て追加/層変更0。

samewall500ms gapを優先、実API NN starts/完成NN/terminal-noNN/backup/採用量/startup/discard/自待ち/旧ACKを別集計して量交絡を併記。samecompletedは量差が大きい場合の後続機構比較候補に留め、同仕事量/同CPUや長期棋力の置換へしない。最大新ply12256・思考6128秒、32job各240秒ならbrowser総7680秒/overhead1552秒で完遂保証0、親04:05:21新heavy停止/04:15:21全終了内で統括が配分。今回はNN/Chrome/game/build0。詳細・missing bound・反証/次判断を残総予算内で固定し提出する。
