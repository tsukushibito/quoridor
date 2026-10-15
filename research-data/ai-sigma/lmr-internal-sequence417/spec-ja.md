# 417：内側の枝・実確認手順の固定仕様

親契約 `.artifacts/research-policy/lmr-internal-sequence-20261015.md` に対応する、Sol/highへの最小実装仕様。設計者はSearch・build・model loadを行わない。旧416の保存結果を保持し、今回の一度の有限比較を別subject `internal-lmr-sequence417-v1` として扱う。

## 入力・選択

416の `inputs-v1/twelve-prefixes.json`（SHA256 `75e417572078a3d20c5d3c0b8e46afad46790dd18ac2e5c925098cd8c5a75c1a`）の12root・既存順序・evaluator/model・完全履歴を固定。Control/PVS/TT1048576/LMR depth_rank、approx/safe/他observer OFF。各rootを独立した空TT・初期orderingからD5、1M nodes、time limitなしで一度観測する。

採取対象は **iteration_depth=5、parent_depth=3、parent_ply=2、eligible=true** のみ。rankはTT-firstを含むdistinct-handの1始まりで、再探索で加算しない。

- **H0の2 slot**：q=0かつrank4..8。DFS訪問順で、同じ仮説の既採取枝とは**異なる親完全履歴**に属する最初の2枝を、返値を見る前に予約する。予約後の中断でもslotを他枝へ交換しない。
- **H+の2 slot**：実q>0かつ浅いscoutが完了しshallow≤保存alpha。完了順で、同じ仮説の既採取枝とは**異なる親完全履歴**に属する最初の2枝。d3では式の上限d−2により正qは1だけであり、q2枠を要求しない。

全slotで「親の完全履歴＋action」の重複を除く。同じ親をH0とH+が共有することは許すが、同じ枝の重複採取はしない。完全履歴の同一性は現 `same_history` の盤面・rules・ply・repetition countsによる照合を再用する。最大4枝の保持済み情報だけで判定でき、全訪問の集合を作らない。

対象外の反復・深さ・ply・rankや別rootで不足を埋めない。候補条件に沿って最初の2親を探すことと、採取済みslotの交換は区別する。coverageは対象gate内だけのrank4..8/9..15/16..31/32+、q0/q1別の機会・初回完了・fail-low・選択/同親skip/同枝skipを小さい固定counterで保持する。旧416のd3/d4・反復横断counterと混ぜない。

rootは終了・親復元を確認してからarmへ進む。rootがD5を完了しない場合はそのrootのarmを未実行UNKNOWNにし、採取しかけたslot・stop・実仕事量を保持する。cap/error/cancel後に他root等で予定分母を補充しない。取消・errorの残り処理は既存停止手順に従う。

## 比較する実手順

保持slot順H0-0/H0-1/H+-0/H+-1で、各枝のarm順序を **N1→R1→R2→N2** に固定する。各armは親の完全履歴、captured PlayedMove path、parent ply2、action、親STM、post-TT/pre-child alphaを一致させる。窓は常に親視点 `[alpha,next_up(alpha)]`。元parent betaは参照として残すが、ここではfull-windowを実行しない。

各armの開始ごとに新しい空TT1M、初期continuation/killer、scratch・accumulator・共通Search stateを作る。容量・score domain・同じ不変evaluatorを揃え、前armのTT/order/scratchを再用しない。元rootのTT等も使わない。論理的なcoldであり、OS cache・allocator・CPU cacheや初回model準備まで同一状態に戻したとは主張しない。追加warm-up Searchは行わない。

- **N**：共通 `state.child` をnormal depth **2** で1回呼ぶ。
- **R**：H0はprobe内だけextra=1、H+は元の実q=1を使い、共通 `state.reduced_child` の `[normal=2,reduced=1]` を1回呼ぶ。shallow>alphaの場合だけ、**同じstate/TT/order/scratch・同じalpha・残りnode予算**でnormal depth2を確認する。shallow≤alphaならそのUpperを返して終了する。

Rの確認でsession・TT・generation・ordering・統計・budgetをresetしない。N/Rともarm全体で100k nodes、time limitなし。Rの浅い段が完了しても確認がcap/cancel/errorなら最終結果はUNKNOWN。R fail-lowで正常終了した時はprotocol COMPLETEだが、**返値を得たchild depthは1、normal targetは2**である。この二つを `completed_depth=2` 一つへ潰さない。

R確認後の値はそのまま保存し、Nの同深さの値と一致すると仮定しない。通常kernel内のLMR/TT/PVS/goal/threefold/undo/取消処理は現行のまま。root処理への置換や追加full-window、通常深さをWDL oracleとする扱いは行わない。

## 計時・件数

`kernel_elapsed_ns` は、共通の親準備・child storage作成が済んだ後、N/Rのdispatch直前から、単一child又はreduced_child全体のreturn直後までを同じ外側境界で測る。Rでは浅い段から必要な確認・undoまでの連続実時間を含む。途中の`?`で計時結果が失われないよう、Resultを受けて終端時刻を確保する。記録用の段別時計・毎node時計は追加しない。

`whole_elapsed_ns` はcallerからarm関数を呼ぶ直前から、局面再構成・TT/order等の生成・kernel・復元検査・局所状態dropを終えて戻った直後まで。JSON整形/出力と返却record自体の後日のdropは外側と明記する。既存の広い `SearchResult.elapsed` を新しいkernel時間へ改名して流用しない。whole−kernelは残余であり、純粋な初期化費とは呼ばない。内包時間をwholeへ加算しない。

raw nsを4armとも保存し、N1/N2・R1/R2の差を隠さない。時計の実効分解能は校正していなければUNKNOWN、ゼロ値・同値・初回wholeの突出も保持する。新たな反復や時計校正Searchは行わない。二反復で十分な費用差を判別できなければ費用結論をUNKNOWNにする。

上限は **12 root＋48枝×4arm=204 top-level entries、12M＋19.2M=31.2M nodes**。Nは最大96 child calls、Rは最大96 shallow＋96 confirmationなので、**root＋明示child callは最大300**。kernel再帰内のchild数とこの明示入口数を混同しない。未開始arm、未実行確認、実開始top-level/child数、root/arm実nodesを分け、確認でcapを復活させない。

## 最小field

| 群 | 保存する意味 |
| --- | --- |
| root/input | 既存FileRefs・元12例ID/群名・fullprefix/完全履歴・image/model/domain/settings、iteration/stop/完成深さ/実nodes。旧勝敗群は由来のみ |
| branch | hypothesis/slot、対象内visit連番、iteration5/d3/ply2/rank、action、original_q、親STM/完全履歴/path、post-TT alpha/beta bits、既存TT/保護facts、元stageのdepth/window/valuebits/bound/完了 |
| arm | arm index0..3、N/R・repeat番号、probe_extra（H0も1）、cold条件、normal_target2/reduced_target1、100k累積cap、開始/完了/UNKNOWN・stop |
| stages | 実child呼出し数、shallow/confirmation有無、各実depth/window/valuebits/bound/完了。confirmationは条件成立・呼出し開始・完了を区別。段の無い値はnull |
| final/work | 最終valuebits/bound、実returned_child_depth、protocol_complete、arm全体nodes/evals等の既存work、親/path復元。エラーで不明なworkはUNKNOWN |
| cost/repeats | kernel/wholeのraw ns、N1=N2・R1=R2の非時計結果/仕事量/段数の一致。費用差を期待してrawを除外しない |
| coverage/counts | 対象gate内の固定counter、採取slot/不足、実root/arm/明示child数とnode分割和。上限を埋める再試行なし |

U/Lは同じscout窓に対する上界/下界。R最終値はshallowか確認値かを明記する。H+の元warm shallowとR shallow、NとR final、確認がある場合のNとR confirmationを別々に照合する。H0には元shallowは存在しないので元normalとNを対応させる。PVが親actionだけならfull child PVと呼ばない。

## 実装・検証の境界

現 `lmr_observation416.rs` のbounded observer/同履歴比較/親復元、`alphabeta.rs` のcommon cold invocation、`measurement.rs` の単一出力入口を延長する。通常呼出しの `search_in_table::<false>` を維持し、診断OFFへ追加allocation・scan・時計・counterを持ち込まない。

具体的には、選択をtarget gateと各仮説2 slotへ変更し、cold invocationへN/Rと二深さを渡す。cold dispatchで共通child/reduced_childを選ぶ。R段の記録は**既存bounded frameを単一arm記録用に再用**できる。その場合は対象parent ply/actionのstageだけを保持し、arm内で新たなbranch選択・coverage収集をしない。これによりreduced_childの制御を別実装へ複製する必要がない。同じframe計測方式をN/Rへ適用し、診断の有限な記録費もkernel時間に含まれると記す。

旧416実行API・二本の独立scout専用経路を互換目的で残さず、唯一の現役診断としてcaller/出力版を更新する。旧416の成果物は不変、過去コードはGitで保持する。独立した探索loop・全TT snapshot・汎用replay/registryは作らない。ファイル名整理は実装担当の範囲でよい。

関連self checksはtarget gate/予約前後/異親・全slot重複除去/不足保持、N-R-R-N順と各arm cold、R fail-low1段・fail-high2段の状態引継ぎ、累積cap/取消/復元、実depth/window/sign/bound、明示callsとnodes分割和、OFF非時計挙動不変に限定する。Rのstate引継ぎは同じ内部呼出しと統計を確認し、偶然TT hitが出ることだけを証明にしない。source境界の独立確認・software/image・一度の有限実行は324の担当であり、設計者の再承認を入口にしない。

## 保存分析の規則

評価器/H0/H+別にNとR finalのU/U・U/L・L/U・L/L、R確認の有無・同深さ値差、原warm対cold、cap/UNKNOWNを分母付きで示す。N1/N2・R1/R2の非時計結果が一致しなければ、その枝を黙って平均・除外せずrepeat disagreementとして保持する。

費用は各枝の4 raw値とN平均/R平均の差を示し、同arm内の二反復差も併記する。効果差が反復差と同程度なら判別不足とする。この判定は記述的な目安で、有意性検定ではない。局所確認費をwhole探索・旧勝敗・一般見落とし率・棋力へ外挿しない。係数候補の新設・自動追加実行はしない。

設計返却後、417.1は**実装・有限診断の保存結果待ち**として所有を保持しcloseしない。結果が届いた時にRootの同じchildへのfollowupで同leafの解析を再開し、検証後にclose/backupする。周期poll・役割追加・再帰委譲は行わない。
