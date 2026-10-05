# frame19 native同wall探索的対局の独立裁定 / 238

現在は選定前静的段階。ready/showgoal+self/no pause/本人割当を確認してclaimした。新180秒/CPU0/RAM512guard448、新4MiB/guard3MiB/forecast2MiBを既poolに計上、旧229270/最終NOT_RUNと旧23490接続有限PASSを保持する。

## 選定前最大1懸念

親のcomplete-response受信時にmonotonic `now-t0<=100ms` とgeneration一致で採用を決める。setTimeout未発火や子内部90msだけを配送期限内の証拠にしない。同core計算で親timer callbackが遅れ得るため、遅い完成応答を事後採用しない。受信時overshoot/完成depthを保持し、shared harness時計不成立はエンジン棋力敗北と区別する。これは結果前ルールの最小明確化で、新run/承認gateではない。

現在小arenaを優先する情報価値は、rootmean蒸留の利益とminimaxleaf/cheapDの同wallノード機会を初めて区別することにある。8slotを固定し結果後の好成績継続・補充をしない。rootbest-firstとnode-contextは別介入として扱い、現在sourceの静的妥当性だけで速度利益を認定しない。NI/最高棋力/RustWasm性能は対象外。

## 検算範囲

停止source/子/background cleanup/currentSHAと正frame19 runtime/実物理を事前束縛。専用argv/task/schema/outputを開始前記録し、最大2小job・累積calc90内で公開全planned/perply/clock/rootlegal/result/費の必要算術と共有RuleA再生だけを検討する。全deep/原teachertruth/旧test/173は再監査しない。完成depthが異なる比較、failsoft/bound/argmax未記録、合法cacheと包括spanの独立性限界を残す。


## 停止後独立有限裁定

専用238 schemaで算術と共有RuleA再生を実施し、全8slotは **2勝5敗1UNKNOWN** と照合した。4開始prefixと全8採用prefix、正常終局7局のwinner、旧guard-censor45手は保存棋譜と一致する。296採用手と旧45手の計341手を再生し、P2 169手・jump2手・wall72手を確認した（旧censorを含む）。共有RuleAに依存するため独立したルール実装・全deep/minimax真値・mutable undoの全面証明ではない。

297記録ply中296採用は完全parse/generation/key/history/合法完成Action検証後の配送が100ms以内。slot1 ply4の100.722574ms応答は非採用でUNKNOWNを保持した。NNUE採用147手の配送中央値90.569623ms/最大97.114164ms、D採用149手は中央値90.523486ms/最大95.995961ms。完成depth>=1、最後完成Action、未完成depth非採用、全合法root数と保存履歴を照合した。初期ロード/READYと回収は一手の配送時計と別であり、STOP_ACK後の費を相手思考へ移していない。

preflight fixture protocol f7ca9124、pilot-r2 46f131b7、later4/current b466271bは異なる。旧6fixtureのlate 98.536192ms早期timerを残し、最終protocolを全6fixtureで再認証したとはしない。実8slotの採用配送と非採用は保存行から独自確認済。

全4attemptのknown NN270156、旧pilot inflight actualUNKNOWNの8192保守上界込み278348、guardian40.254772760秒を足し戻した。旧pilot-r1はgit hash-objectの.py引数を科学Pythonと誤判定したguard censorであり、45手と原失敗は科学敗北に置き換えない。background53.843702秒、arena27.202382秒、ロード/READY、inclusive spansはguardianへ重複加算しない。owner cost metadataのpack/Git/LLM/管理全壁時計UNKNOWNは保持し、このtaskで未測値を埋めていない。

ordering-only同node4096の初期NNUEはascending depth1→rootbest-first depth2が2反復で成立する。一般速度・同wall棋力・NIは未認定。対局のprocessed中央値はNNUE1876/D2646だが異なる局面であり、評価費を唯一原因と認定しない。4opening familyの色交換8slotであり8 IIDではなく、2勝はP2側、壁だけの開始prefix群も含む。候補MSEの改善を対局利益へ読み替えない。

次の最大1方向は、239の保存診断を踏まえてrootmean教師（探索平均）をminimax leafへ転用する意味とhorizon/historyのずれを、同開始局面・同完成horizonの最小対照で判別すること。現正常終局7局を消さず、費・深さ差の競合説明を残す。今回は追加科学を要求しない。

### 検算器の失敗と資源

第1jobはledger `status:TERMINAL`を勝敗欄と誤読しexit1。失敗版・最初差・ログを保存し、`result_NNUE`との独自winner照合へ修復した。第2job内で算術とRuleA descendant replayを完了しexit0。新NN0、CPU0単1、点peak RSS105979904B<448MiB、親子はwait済（JS単独PIDtickは未保存）。第1job23:29:01.803825→01.869510/0.065722秒、第2job23:30:07.418717→07.590608/0.171934秒。source90+calc45+45=180/180保守charge、2job上限内。旧229final NOT_RUN/270と旧234PASS/90等は不変。直前current frame19 loadedbinding/ownedNone/物理子/RAM/GPU/保存をbindし、点証拠を全host/未来の不在保証へ広げない。

入力・算術・失敗・停止の正本は `research-data/ai-sigma/frame19-native-independent/` のstopped-inputs、clock/replay-result、各admission/process、checker-repair、science-stopを参照。科学受付・有限支持・棋力目標達成を分離し、goal未達を保持する。

時計分類補足: slot1は合法valid=true/completeddepth2のRESULTがparent100.722574msで届き、searchwhole95.027186ms。無応答/NO_COMPLETED_DEPTHではなく、期限内採用応答なしとしてUNKNOWN/late discardを保持。独立jobのfault response_present=trueと全297記録/296採用に整合する。valid/depth/wholeの追加詳細は後着239/coordinator receipt参照、追加checkerjobを実施して再認証したとはしない。180/180・2job停止不変。
