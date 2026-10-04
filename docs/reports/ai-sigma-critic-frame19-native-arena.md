# frame19 native同wall探索的対局の独立裁定 / 238

現在は選定前静的段階。ready/showgoal+self/no pause/本人割当を確認してclaimした。新180秒/CPU0/RAM512guard448、新4MiB/guard3MiB/forecast2MiBを既poolに計上、旧229270/最終NOT_RUNと旧23490接続有限PASSを保持する。

## 選定前最大1懸念

親のcomplete-response受信時にmonotonic `now-t0<=100ms` とgeneration一致で採用を決める。setTimeout未発火や子内部90msだけを配送期限内の証拠にしない。同core計算で親timer callbackが遅れ得るため、遅い完成応答を事後採用しない。受信時overshoot/完成depthを保持し、shared harness時計不成立はエンジン棋力敗北と区別する。これは結果前ルールの最小明確化で、新run/承認gateではない。

現在小arenaを優先する情報価値は、rootmean蒸留の利益とminimaxleaf/cheapDの同wallノード機会を初めて区別することにある。8slotを固定し結果後の好成績継続・補充をしない。rootbest-firstとnode-contextは別介入として扱い、現在sourceの静的妥当性だけで速度利益を認定しない。NI/最高棋力/RustWasm性能は対象外。

## 検算範囲

停止source/子/background cleanup/currentSHAと正frame19 runtime/実物理を事前束縛。専用argv/task/schema/outputを開始前記録し、最大2小job・累積calc90内で公開全planned/perply/clock/rootlegal/result/費の必要算術と共有RuleA再生だけを検討する。全deep/原teachertruth/旧test/173は再監査しない。完成depthが異なる比較、failsoft/bound/argmax未記録、合法cacheと包括spanの独立性限界を残す。
