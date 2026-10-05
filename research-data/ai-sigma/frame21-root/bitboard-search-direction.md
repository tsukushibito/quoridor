# ユーザー意図: ビットボードによる共通探索/経路高速化を優先候補へ

ユーザー「探索高速化もビットボード化したほうがよいよね？」を受け、Claustrophobia固定ae093653のu128 bitboard/flood_step方式を次の有力実装候補へ入れる。現在267のfixed81queue対照を途中で別条件へ差替えず、自然停止/登録前または次runで費と残時間に応じて選ぶ。同scope内の残費で成立すれば実装・検証・測定まで進め、当初一介入という粒度を永久的高速化禁止にしない。新上限/枠延長/追加取得0。

現行main PositionはH/V配置u64だがwall_distanceはVecDequeとseen[81]のセル逐次BFS。したがって『壁は既にbitset』と『経路展開をbitparallel化』を区別する。参考source: https://github.com/Plaaasma/Claustrophobia/blob/ae093653e62ad700e201706fa5ed767093d0d68e/src/bitboard.rs 。u128下位81bit、H/Vの遮断edge mask、上下±9/左右±1 shiftと盤端mask、frontier/reachedを用いた層ごとの展開。bitparallelは複数マス集合の同時演算でありthreads増ではない。

優先対象はcoreの最短距離/到達可能性と合法壁判定。共通core変更でαβとMCTS双方へ届く範囲を確認する。NNUE壁距離map/cacheやSigma入力mapは別callerなので、共通化/再用できる箇所と未変更範囲を明記。駒jump/斜め、壁交差/重複/両pawn経路存在、不可達、P2、make-unmake/history/terminal等の規則を省略しない。wholemapのmaterialize/キャッシュ更新費も測り、u128利用だけで全葉高速化を保証しない。

既fixedqueueをoracle/controlに使い、固定合法prefixと壁候補/距離/到達に対応を確認してからrelease同仕事・同Kで差を測る。ノード/NN/K/model/品質を維持したcore費、αβ探索費、教師生成の有効行/全job秒を分ける。現在Rust/native優先、Wasm製品は後段の必要対応。CPU/RAM/保存/owner/measurement競合を既配分内で調整。新構造へ全面置換や既測定成果の救済を義務にしないが、有望候補として具体実装機会と担当を現在計画へ残す。

rootはcore/ai sourceへの並行編集・Git/index操作0。統括と267の既ownerで調整し、提案/実開始/実利益を分けて報告。今回の主feature/learning課題と探索高速化の優先度、frame終了10:37:54UTCは維持。
