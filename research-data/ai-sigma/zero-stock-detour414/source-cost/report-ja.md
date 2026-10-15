# 414: 壁迂回lower boundのsource費用・実装可能性

**一つのboundを既存411のgeometry判定に差し込む小変更は可能です。ただし今回は計画のみで、production patch・実装・test・数値実行は0です。追加時間、証明件数、速度利益はUNKNOWNです。**

対象はimmutable Main `ea6f2834d65de92479e5e5ce505d37b8f8b08c97`。alphaの実SHA256は0391bcd26f0f20f873af9c0bfe0567852bdf87cc70f5aa824d78d30b42e4e86e、161687Bで、固定411距離owner＋412のmechanical defaultです。source-refs/followup-refs/insertion-refsに各Git blob OID・hash・bytes・lineと選択fragmentのSHA-size-modeがあります。全sourceのmirrorは残しません。

## 実際の既存owner

現役`WallDistanceScratch`に`canonical_pair`というAPIはありません。private `maps: Option<WallDistanceMaps>`がH/V keyと`[[u8;81];2]`を保持します（alpha:103/109/115）。`distance`は有効なcached pairを優先し、次に同H/VのScratch pairを読みます。stock0でpairがなければ**既存411自身が**`p.wall_distance_maps()`を一度呼び、次のdistance参照に再用します。positive stockでmapがなければ既存scalar `wall_distance`へfallbackします。

Floatでは`cached_distance_maps(p,[pooled,parent])`（alpha:157）が既に正しい候補を選びます。他variantをFloatと扱いません。`Accumulator::cached_wall_distance_maps`（nnue/lib:208）→`WallMaps::distances_for`（nnue/features:23）がH/Vの完全一致を要求します。parentやpooledのstaleなkeyをそのまま使いません。pawn/turnが違っても同じ固定壁geometryのgoal-distance表である点は元のowner契約です。map構築の正本はPosition::wall_distance_maps（core/position:187）→一つのWallEdges準備＋両playerの既存distance_mapで、414用BFSは作りません。

fixedDも同じ`EvalScratch.distances`を使ってown/other距離を取得します（alpha:253）。通常Searchは`evaluator.create_scratch()`をSearchの一invocationが所有（alpha:2872）。単独direct evaluateは自分のdefault scratchを作ります。同じownerでも寿命を混同しません。Scratchは一pairだけでH/V変更時に入替わり、invocation終了でdrop。Float参照は既存accumulatorから借用し、Arc/map/81配列をcloneする必要はありません。既存pairの情報bodyはH/V16B＋162B=178Bですが、padding/Option/ABI/stack/RSSは未実測UNKNOWNで、この178Bを414追加割当と呼びません。

## 最小の差込案と追加作業

一箇所は`Search::safe_race_value`（alpha:1607）。既存SafeRaceLeafの完全資格TT hitは距離取得前にreturnするので、そこでの追加map参照は0です。TT miss後に得た`cached`・`ds`・`other`・pawnsを再用します。ds/otherはそれぞれD_s[p_s]とD_other[p_other]で、sはturnです。

まず既存Manhattan Mで411 predicateが成立すれば同じwinnerを使い、cross参照を省けます。UNKNOWNの時だけ、既にqualifiedなFloatの`cached`を借用、または同じprivate moduleからScratchのOptionと同H/Vを確認して`&distances`を借ります。新getter/API、builder、cache ownerは不要です。

| 経路 | 414の追加scalar参照 | 必要なguard |
| --- | ---: | --- |
| 資格あるSafeRaceLeaf TT hit | 0 | 既存fullhistory/context/depth/domain/bestNone |
| Mだけで証明済み | 0 | 既存411条件を維持 |
| MはUNKNOWN、真のpairあり | 2 | 追加cross値ごとに<81。ScratchならOption＋H/V2比較 |
| pairなし/不一致 | 0、強化しない | 既存M結果/UNKNOWNへfallback。構築しない |

追加は`D_s[p_other]`と`D_other[p_s]`の2つのu8配列読取り。own側のds/otherを再度読む必要はありません。各crossが<81なら対応するabs_diffを取り、Mとのmaxを二段で取ります。数学上のrow名D0/D1とturn基準のown/otherを取り違えません。両方向を独立に有限判定し、一方だけ無効ならその項だけ除きます。2つとも無効ならL=Mです。81を通常距離として引き算しません。own値とpawn indexは既存2回のdistance/root contextが既に資格付けています。

L=max(M, finite abs(D0[a]-D0[b]), finite abs(D1[a]-D1[b]))。追加処理の上限形は2finite比較、最大2 abs_diff、2 max、必要ならL>M判定と既存threshold判定もう一度です。コンパイル後の命令数/時計はUNKNOWNです。Mで成立済みのfast pathを残すのは同じL候補の不要計算回避で、別候補やthreshold変更ではありません。

pairを見つけるために`distance()`をcross-pawnへ再呼出ししてはいけません。これはread-only accessorではなく、map構築/scalar BFSに進み得ます。偽のpawn Positionを作る、片方のscalarからrowを再構築、81cell走査/検証、追加pawn BFS、heap/clone/new cache/new selectorも不要です。現在のeligible stock0でds/otherが取得済みならFloatかScratch pairが通常既にありますが、このsource上の関係をdynamic hit頻度とは呼びません。保守的fallbackは「既存pairが確認できなければ強化しない」です。

既存ds/other取得に要するFloat照合、Scratch構築/再用、WallEdges/BFS費は411/410の元の距離取得費です。414だけの新費用へ二重計数せず、逆に隠しもしません。map_readsは現在distance内部の参照を数えるcounterで、将来の直接cross参照2回は自動では反映されません。既存counterだけから新しい全map traffic/費用を推定できません。今回はcounterや計測codeを追加しません。

## 保持する境界と未確認事項

同じtrue wall-key上の有限goal-distance差を使う一候補です。これを新しいgameWDL solverや棋力証拠とは呼びません。411のds<=doかつbound>=2ds、do<dsかつbound>=2do+1という十分条件、goal/threefold優先、positive childdepth/双方stock0、root通常手比較、depth0通常評価を保持します。geometry成功後だけcomplete empty Eを調べ、履歴不適格を迂回しません。TTのfullhistory/context/depth/domain/leaf kind、None best、enter/control/make/undo/取消/error/NNUE skipのonce会計も保持が必要です。将来の実装/namespace意味版/数学確認はRootの別の実許可範囲で扱い、この計画はそのclearや採用ではありません。

実装clock・native・tests・Search・旧WDL/edge/rank solverは0。追加時間、map利用率、Mを超える件数、判定利益、cache/RSS/汎用speed/default効果は全てUNKNOWNです。CPU12/guardian0/family512MiB/GPU0/hostreserve4GiBを現役guardで実制御し、available affinity/distinct physicalと対象physical core上の瞬間的なpinned research peer不在を記録しました。global/futurequietやidle leaseではありません。LLMのhost CPU/RAMはUNKNOWNです。

最初に推測したresource module pathが不存在、try_safe_race/Stateという名前が実sourceには不存在だった事実を保持。実owner safe_race_value/Searchへ限定して追加読取りしました。followup importが一度同じimmutable intakeを重ねたため、helperへmain guardを付けて以後の反復を止めました。数値/geometry/test再実行はありません。原capturesと凍結411/412/413は変更していません。actual STOP/reader-child/directwait/reap/freshidentity/handles/TMP/owned[]と一度のOWN使用量はSTOP.jsonにあります。

Root324がMain/Git/index/Cargo/Beads/status/backup/closeを所有し、412/413 LMRが優先です。production patch・dummy mode・new API・新実験の発行は0。mixed/learner全prep-pipelineと323 USERPAUSE、製品/generator enableOFF、models/weights/seals/oldfits96/foreign/旧RAWFAILED費UNKNOWNを保持します。
