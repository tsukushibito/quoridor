# frame20 実対局D分岐rootの有限horizon診断

目標と選定理由:249同100msの相対WDLはclip/tanh各NNUE2W2L。253による同completeddepthのD Action差6列は、slotclip4/tanh3・ply44の同一root1個、depth1..6に集中し、旧240/248exact四caseとはboard/fullhistory不一致。未知の値/tieを旧caseから移植できない。この実対局rootだけの同入力depth1/2で三評価器の全合法rootchild有限値・極値由来を得て、次のleaf意味/history/horizonか探索費の優先を変える。新勝敗反復、追加生成、低LR学習、全TTより入力対応の判別力と薄接線5–10min/単job90sの全費を優先。真の悪手/一般棋力はこの診断で認定しない。

Owner experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746、cwd/model/effort既設定。249closed/source科学stopcf5db480/current29source7payloadをreadonly再用、全旧3job/費・UNKNOWN・期限をreset0。solewrite tools/ai-sigma-frame20-one-root-leaf/、research-data/ai-sigma/frame20-one-root-leaf/、report docs/reports/ai-sigma-experiment-frame20-one-root-leaf.md。他role/source/runtime書込0。

固定入力:249aggregate SHAa8305b82のD matched slot_clip4/slot_tanh3/ply44、同board+実STM+全記録count-history+exactprefix一致、historySHA0ec475d57131761ec8c0948a75c9802f5f3354272856e34f7bdc30487ad25d0c。253saved-correspondence/preregisterはmetadatareadonly、rootは同249原hands/resultから元buildState/RuleAで復元しboard/history/STM/P2と入力SHAを登録。別root代替/旧機械case追加/新opening0。253全文/Git/251全稿はgateにせず、必要入力SHAと固定selectionだけ束縛。

六条件結果前固定:depth1のNNUE,Dclip,Dtanh→depth2のNNUE,Dclip,Dtanh。凍結228576BEST2000同tensor/scale/f32STM/runtime標準化、D係数rawuとclip/tanhは249同版、terminalwinner±1/200draw/noLegal0先判定、fastleafpackage/fullfallback/完全RuleA-history保持。全合法rootchildそれぞれfull-windowで有限depth値を記録し、全集合/tie/min/max/次候補gap/元採用Action21/29のargmax所属を保存。履歴を消した対照/terminal校正変更/再fit/新NNUE学習0。

root順は登録した全legalAction順、元順が保存に無ければAction昇順を診断順として明示。strictfirstの違いを元rootbest-first tie改善やバグへ付替えない。内部TT/noise/policy0、全合法維持。各childのfinite-horizon値とminimax極値の終局/非終局由来、Dpretransform u/pre/post/value domain、NNUE非終局値・符号伝播を記録。剪定下で全極値由来を確定できなければprincipal-witness限定/UNKNOWNを明示、訪問leafの存在だけをroot原因にしない。符号/極値集合の軽いsynthetic-terminal/非terminal fixtureと入力復元検査は同単1job内、6conditionの科学分母から失敗を隠さない。追加広いparity/全教師truth/全RuleA監査は入口義務0。

総予算:新科学MAX1/CPU2single/GPU0/Torch0、guardianhard90s/allscience90s、processed合計65536、nativeNN合計20000（初期/fixture/全条件を含む）、RAM1GiBguard896MiB。終了した条件と未処理child/conditionの全予定分母を保存、cap未達を条件変更/再実行で救済0。原counterUNKNOWNはUNKNOWNと20000保守上界を別保持し減額0。source/read保守180s、管理180s。新4MiBを確認unused15835136→11640832B、guard3.5MiB/forecast3MiB。全old予約保持/parent追加/unknowndiscount0。

科学は現在ROLE252 loaded/current24hash/正PIDtick/parentframe20/ownerpause、249全science/backgroundcleanup/source止、253自science0と251実CPU窓に対する本人freshphysics/RAM/GPU/storage/次自然監督quiet>=120からadmit。LLM人数gate0、旧runtimeの不在をnewfreeに代用0。科学窓は既230背景submit→jobIDnotes→Idle→一度completion、現在ownedをinterrupt0。251独立算術と実CPU同時起動0、相手全稿/ACK待ちはしない。

新task/schemaは実issue番号を取得後one-root-leaf-{issue}-v1/one-root-leaf-v1、argv/entry/currentsource/input/outputpurposeを登録・post一致。CPU/model開始とqueue受付を別報告。source02:13目安/科学02:15目安、最遅新入口02:25・全science02:27stop・必要保存02:34。条件が間に合わなければNOT_STARTED/typedmissing、親02:41heavy/02:46scheduler/02:49monitor/02:51:02endは延長0。

引渡しは全6/全legalchildのfinite-horizon値・費・版・gap/tie/originの範囲、源・自己子background停止、必要Gitbyte/defaultindex不変・notesbackup。owner有限検証後同実質turnclose可、独立全稿gate0。結果から次最大1を提案し、自動arena/学習/同rootより深い追加runはしない。これは既選定局面の診断であり未見test/戦略的真値/NI/Sigma同等/最高目標達成ではない。
