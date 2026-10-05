# 次枠候補: 凍結headと距離評価の探索実用対照

206の独立提案を採用候補として保存する。現在枠では実配分・起動しない。2026-10-04 03:06 UTCの確認で、必要な実装・数値照合・4局と回収を既定の03:00新科学開始/03:05停止へ収められない。前の着手予定を実開始とは扱わず、期限を更新しない。

問いは、headの誤差増分が不確かな場合にも、追加評価費と手選択の差に実用価値があるか。204 BEST600（file SHA f9dff330239f56164af96aa97be5a171059aaa732dfa8054e9b6380b7dbcb54f、tensor SHA437b5fde4dc4a4356ec2281759971d3d4937a45e17224cc9303dbdc2dc8dbeea）と距離係数 a=.06294242415104226,b=8.276425107422213を凍結する。head33だけ学習済み、下層は凍結したQF1-H32であり、全面NNUE学習成功とは呼ばない。

次の明示許可枠でexperimentへ単writer配分を具体化する。候補所有範囲はtools/ai-sigma-head-alpha-arena/、research-data/ai-sigma/frame14-head-alpha-arena/、専用報告のみ。190のfull/delta/undoと203のαβ・402cut/411public/500guardをreadonly再用し、P1/P2・壁/駒/undo・終局を有限照合、凍結Torch参照32行以下とのf32差をabs1e-6+rtol1e-6で確認する。旧source/model/test/173正式holdoutを変更・転用しない。

fresh2familyをopening8/16で結果前固定、色交換2pair/4game、HEAD対DISTを同CPU時間のαβで比較する。両者とも原合法順/maxdepth4/8192processednode、同500ms・取消/完成depthのみ採用。特徴更新とNNUE推論は当該player時計へ含める。事前固定の全4slot、合法性、clock、depth、node、評価回数・追加費、RSS、unknown/censoringとWDLを保存。203のDIST対Sigmaの再実行ではなく、HEAD対DISTの探索診断である。少数対局は棋力NI/最高棋力の証明ではない。

配分案は準備CPU2単1/Torch1・RAM1GiB guard896MiB/30秒・参照NN64以下、回収後arena CPU2/4各1と管理0最大3logical/RAM2GiB guard1.75/1job240秒/全heavy300秒、native NNUE評価上限1500000・debug4000。GPU/学習/追加test選定0。新保存32MiB/guard28はexperiment既1980MiB poolの確認済み未使用だけから割り当て、uniqueGit・一時物・最終metadataを先計上する。今回は予約実移転も0。実期限は次枠許可から別途結果前に固定し、準備未完ならNOT_STARTEDとして保存、補充対局しない。

結果から継続・保留・不支持を判断する。追加学習、量子化、policy、ordering、幅/LR/sweep、旧test再開は自動連鎖しない。
