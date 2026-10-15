# 414：壁迂回下界の保存ラベル照合

指定した一候補は、保存W/L 5,680件で旧条件より112件（勝ち76・負け36）多く判定し、false-Provenは0だった。保存D 39,708件はすべてUNKNOWNのまま。旧条件が成立した全件で同じ結論を保持した。この有限確認から一般証明・9×9・Search採用を認定しない。独立414.3の一般論証とは別scopeである。

## 固定候補・入力

`L=max(M, finite |D0[a]−D0[b]|, finite |D1[a]−D1[b]|)`。D0はP0 goal row、D1はP1 goal rowへの壁のみ通常最短距離。両mapは同じ正確な(board size, wall mask)から作る。各差分は両crosscell距離が有限なときだけ採用し、一方が到達不能でもManhattan Mを残す。他方のgoal mapの有限差分まで捨てない。

`0<=d<n*n`の整数だけ有限とし、dictionaryの欠落およびboard-size sentinel以上を到達不能とした。5×5 sentinel25、9×9 sentinel81を実距離へ混ぜて絶対差を取らない。9×9の境界定義は小さい合成値だけで、9×9の盤面計算はしていない。

旧411の判定のMだけをLへ置換：手番側goal距離ds、相手doについて、ds<=doかつL>=2dsならW、do<dsかつL>=2do+1ならL、それ以外UNKNOWN。goal/active非終端の意味を変えず、完全履歴・TT/root/depth・真のterminal保護をこの保存ラベル検査で資格化していない。production Search patchは0。

旧405の52個の保存binary（全47 tiny3×3+固定5個5×5）から既存active W/Lラベルだけを読む。旧52のcheck_fixture/WDL/合法pawn辺/rank検証suiteを再実行していない。409のcompact D flags/3,872 layout対応はその保存authorityを再用し、3,868 WDL復元や全2,532,560配置solverは実行していない。全壁数・偶奇・両手番を保持した。

## 一度の有限結果

| 保存集合    |  件数 | 旧W/L/UNKNOWN | 新W/L/UNKNOWN | 追加W/L | L>M | false-Proven | 未検査 |
| ----------- | ----: | ------------- | ------------- | ------- | --: | -----------: | -----: |
| 52 fixtures |  5680 | 1393/476/3811 | 1469/512/3699 | 76/36   | 540 |            0 |      0 |
| 全保存D     | 39708 | 0/0/39708     | 0/0/39708     | 0/0     |   0 |            0 |      0 |

W/Lの保存真値はW=3,530/L=2,150。新条件は1,981件を判定、残り3,699件をUNKNOWNとした。UNKNOWNを不成立や0件の証明へ変換しない。全保存Dではこの集合に限りL=Mだった。既知Dへ誤ったW/Lを付けたものは0。

| 集合/サイズ     | 検査数 | 旧W/L/UNKNOWN | 新W/L/UNKNOWN | 追加W/L | 片側goal-mapの非有限crosscell pair数 D0/D1 |
| --------------- | -----: | ------------- | ------------- | ------- | ------------------------------------------ |
| all_saved_D/5×5 |  39708 | 0/0/39708     | 0/0/39708     | 0/0     | 0/0                                        |
| fixtures52/3×3  |   1830 | 440/96/1294   | 480/112/1238  | 40/16   | 84/84                                      |
| fixtures52/5×5  |   3850 | 953/380/2517  | 989/400/2461  | 36/20   | 0/0                                        |

壁数/偶奇/手番/ds==do/Mと閾値のbelow-equal-above/Lと閾値のbelow-equal-aboveのjoint strataはresult.jsonおよびpresentation.jsonに全件保存。各stratumのpredicate true/falseとunexaminedを明示し、旧true⊆新true・追加数=新−旧・総45,388件を検査した。

## 保存例

| 追加判定 | side/mask/raw | P0/P1/手番      | ds/do/M/L | goal-map差分 | 保存真値 | 原record                   |
| -------- | ------------- | --------------- | --------- | ------------ | -------- | -------------------------- |
| W        | 3/6/45        | [0, 2]/[1, 1]/1 | 2/6/2/4   | [4, 2]       | W        | fixture5 sha abbe128b24f2  |
| L        | 3/18/11       | [0, 0]/[1, 2]/1 | 5/2/3/5   | [1, 5]       | L        | fixture10 sha 9e53a1df7a76 |

座標は(row,col)、0始まり。raw IDは旧405の二pawn+turn定義のまま。具体例は新条件の結果から記述用に最初の例を採ったもので、検査集合の選別や別trialではない。

## 必要境界と実装範囲

13の小定義を今回だけ確認：有限crosscell差、5×5到達不能25、9×9到達不能81と有限80、欠落値、片map非有限でも他方有限差とMを保持、W/L閾値の等号と1未満、goal距離tie、wall key不一致とboard size不一致の拒否。実board mapsは旧405 board/409 distancesの正確なAST関数だけを呼んだ。source全体のトップレベルやpawn-actions/oracle/check_fixture/retrograde/shortest-DAG-pair探索は実行していない。

有限sampleで誤判定がないことは、境界条件や一般定理の証明ではない。9×9/実全履歴、TT bound再利用、depth/root/terminal gate、actual method/image/clockや性能利益は未検証。今回のsourceは私有の有限保存検査であり、製品/研究Searchコード・既定値へ統合しない。

## 費用・参照・停止

原math-v1を一度だけ実行。child内部計時 1.764705522s、self ru_maxrss 28659712B。外側executeの実wallはmath-v1/return.jsonの1.920527222sでnested、両方を加算しない。LLM/全作業費・continuous family RSS peakはUNKNOWN。

実worker CPU8、guardian/controller11、source family512MiB、math family1GiB（child960MiB+controller64MiB）、GPU0、host reserve4GiB。両coreのfresh topologyとcpuset/quotaはcontroller.jsonへ保存。affinityだけで他のtimingとの公平性を認定しない。Main/canonical/hardware leaseを保持していない。

全57参照はSHA-size-modeをparse前と読取後に一致確認。原selected reader STOP 2026-10-15T09:15:17.057865+00:00。Source/helper/formatterのdirectwait/reap/fresh exact identity/handles/TMPcleanup/全owned[]はSTOP.json、FileRefsはselected-refs.json/completion.json、対象usageはusage.json。元405/409/411 source/results/RAW/image/census/feesを変更していない。

初回Ruff lintは小文字lの曖昧変数名2箇所で失敗し、math entry前に名称だけ修復。原capture/returned NULLとdisk pending/attemptedを保持し、数学runは1回・再演0。presentation-v1は総和のhardcoded表記43388が誤りで停止した。5680+39708=45388へ報告チェックだけ修復し、原失敗を保持、predicate照合は再実行していない。新model/forward/Search/arena/game/solver/build/新WDL/旧成功52suite/threshold sweep/代案選定0。Root324がMain/Git/Cargo/Beads/backup/closeと重要解釈を所有し、別reviewをdispatchしていない。

mixed/learner全prep/pipeline、323 USERPAUSE、product/generator enableOFF、models/defaults/weights/seals/oldfits96/foreign変更/全旧RAWFAILED費UNKNOWNとdecimal50GBを保持。一般論証や親close/返信ACKをこの有限保存検査の追加条件にしない。
