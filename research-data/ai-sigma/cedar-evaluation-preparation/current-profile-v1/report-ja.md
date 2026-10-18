# 現行Cedarの実CPU profile：固定4局面・12 calls

**今回の上位resolved selfはhead 17.50%、壁距離15.00%、合法手生成11.875%、validation10.00%、delta owner8.4375%。** 同じgroupを分割したものやinclusiveとの重複を足さない。17.5%を取り除ける時間とは解釈しない。最適化は採用していない。

## 実行と分母

genuine image226ceecb / BUILDfabd58d8 / sourcef5f452b、Cedar weights35cbb976・typed eb0fbc93、FT32/H32/FP32/zero4、Control/PVS、LMR ON/depth_rank、path_tail ON、TT1M、approx OFFを固定した。現HEADのdocs変更をimage更新とは扱わず、symbol/モデル408/旧suiteの再Build・再資格を行っていない。

原Cedar8の既存compact projection op00/slot0/family0の一局から、残壁帯11..20／5..10／1..4／0で最初のaccepted parentを保存順に選んだ。ply4/28/48/61、残壁16/10/4/0、色0/0/0/1。**一つのfamily・一つのゲームに依存した4局面**で、4独立標本ではない。opening＋実着手の完全prefixを固定し、全12entryが現nativeのcanonical replay/normal/fullhistory/非終端資格を通り、synthetic=falseを確認。from_countsで年代順を代用していない。元32archive/旧perf RAW再decodeは0。

plain4→profile4→plain4。各callは独立native process／fresh TT1M・initial orderingのcold session、D8・1M nodes・timeNone。warm条件は未測定、warmupなし。診断observer/LMR observer/completed-depth callbackはOFF。seedを消費する入口はなく、requested/effective seedはnull。

実12calls/12sessions、9,000,099nodes、7,226,733報告logical evaluations。3 DepthComplete＋9 NodeLimit UNKNOWN、Err/復元不整合/追加call0。UNKNOWNを要求D8達成へ昇格せず、3M弱の未使用node枠を補充していない。全4入力でplain二反復とprofileのvalue bits/action/exactPV/depth/stop/**全work counter**/親fullhistoryが一致した。

| 入力/元ply/残壁 | 各call nodes | completed depth / stop | delta / logical eval | P proof leaves | 数値TT cutoff |
| --------------- | -----------: | ---------------------- | -------------------: | -------------: | ------------: |
| high / 4 / 16   |    1,000,000 | 5 / NodeLimit          |    999,995 / 846,020 |              0 |         2,109 |
| mid / 28 / 10   |    1,000,000 | 6 / NodeLimit          |    990,013 / 795,380 |              0 |        14,939 |
| low / 48 / 4    |    1,000,000 | 6 / NodeLimit          |    928,816 / 767,507 |         70,863 |        10,223 |
| zero / 61 / 0   |           33 | 8 / DepthComplete      |                4 / 4 |             21 |             0 |

lowでは70,863 proof leafが既に評価更新を迂回し、zeroでは21 proof leaf・4 delta・4 logical evaluationsだけだった。これをNNUEの物理FT/head実行数へ変換しない。typed proof/terminal/通常TTは異なる境界である。

## 現CPU hotspot

`cpu-clock:u` 99Hz、DWARF user stack8192B、ring64 pages、no-buildid-cache。入力別RAW上限2MiB・計8MiBに対し実2,781,968B。全RAWを保持、cap到達なし。既存ELF .symtabとCFA/unwindだけを用い、.debug_infoはない。

**320 samples**、period合計3,232,323,200（cpu-clock単位、約3.232323秒分）。これはsample periodの和で、正確なprocess CPU clockやwall durationではない。perf recordの表示sample数とparser全数が一致、lost event観測0・未解析行0。leaf unresolvedは22/320、全320/320 chainにunknown ancestor/sentinelがあるため、完全なunwindやinline分解を保証しない。inclusiveはresolved named ancestorの範囲である。

| 責務group                                       | 全体self % | 全体inclusive % | high self % | mid self % | low self % |
| ----------------------------------------------- | ---------: | --------------: | ----------: | ---------: | ---------: |
| residual head（pack/演算を含むowner＋AVX2 dot） |     17.500 |          23.125 |      26.087 |     14.912 |     13.393 |
| 壁距離全体（repair/単goal BFS/全map）           |     15.000 |          16.562 |       8.696 |     16.667 |     18.750 |
| 合法手生成・両goal到達性                        |     11.875 |          12.188 |      11.957 |     12.281 |     11.607 |
| validate/checked_positionsの独立symbol          |     10.000 |          10.000 |       8.696 |      7.895 |     13.393 |
| delta_move_into owner（FTだけではない）         |      8.438 |          27.812 |       5.435 |      7.895 |     11.607 |
| 履歴・make/undo・checked transition             |      6.875 |          13.750 |       7.609 |      7.018 |      6.250 |
| TT probe/insert・board/context fingerprint      |      5.000 |           5.000 |       4.348 |      7.018 |      3.571 |
| continuation history採点                        |      3.750 |           3.750 |       5.435 |      3.509 |      2.679 |
| ordering/prepared/ordered owner                 |      1.562 |           1.875 |       3.261 |      1.754 |      0.000 |
| うちwall_distance_maps_after_addition           |      9.062 |          10.000 |       6.522 |     11.404 |      8.929 |
| うちwall_distance                               |      5.312 |           5.312 |       2.174 |      5.263 |      8.036 |
| ID更新の独立symbol                              |      0.000 |           0.000 |       0.000 |      0.000 |      0.000 |
| FT列kernelの独立symbol                          |      0.000 |           0.000 |       0.000 |      0.000 |      0.000 |
| copy/memmoveの独立symbol                        |      0.000 |           0.000 |       0.000 |      0.000 |      0.000 |
| 標準sortの独立symbol                            |      0.000 |           0.000 |       0.000 |      0.000 |      0.000 |
| allocatorの独立symbol                           |      0.938 |           1.250 |       1.087 |      1.754 |      0.000 |

0.000は**このsymbolとしてsampleが無い**という観測で、費用ゼロではない。ID clone_from/remove/insert、FT row copy/add_column、finite scanの一部はinlineまたはdelta ownerに含まれ、孤立したself費はUNKNOWN。maps_for自体も独立symbolとしては未解決。map repairと単goal BFSはwall-distance全体の部分集合である。checked_positionsはvalidation/history両groupに現れる。

| 上位self symbol（全入力）                                                | samples | self % |
| ------------------------------------------------------------------------ | ------: | -----: |
| `<quoridor_nnue::residual::ResidualModel>::evaluate_with_scratch`        |      32 | 10.000 |
| `<quoridor_core::position::Position>::wall_distance_maps_after_addition` |      29 |  9.062 |
| `<quoridor_nnue::Model>::delta_move_into`                                |      26 |  8.125 |
| `quoridor_nnue::simd::avx2_dot_fast`                                     |      24 |  7.500 |
| `<quoridor_core::position::Position>::legal_action_ids`                  |      24 |  7.500 |
| `<quoridor_core::position::Position>::wall_distance`                     |      17 |  5.312 |
| `[unknown]`                                                              |      15 |  4.688 |
| `<quoridor_core::position::WallEdges>::both_reachable`                   |      14 |  4.375 |
| `quoridor_nnue::validate_features`                                       |      14 |  4.375 |
| `<quoridor_nnue::Model>::validate_accumulator`                           |      13 |  4.062 |
| `<quoridor_core::research::SigmaContext>::is_repetition_draw`            |      11 |  3.438 |
| `<quoridor_ai::alphabeta::continuation_history::PositionScores>::score`  |      10 |  3.125 |
| `<quoridor_ai::alphabeta::Table>::probe_hashed`                          |      10 |  3.125 |
| `[unknown]`                                                              |       7 |  2.188 |
| `<quoridor_ai::alphabeta::Search>::child`                                |       7 |  2.188 |
| `<quoridor_core::research::ContextUndo>::checked_positions`              |       5 |  1.562 |
| `sha2::sha256::x86::digest_blocks`                                       |       5 |  1.562 |
| `<quoridor_ai::alphabeta::Search>::ordering_scores`                      |       5 |  1.562 |

headは高残壁26.09%に対しmid14.91%・low13.39%、壁距離は8.70%→16.67%→18.75%と、この4局面では構成が違う。wall_distance_maps_after_additionとwall_distanceの両方が実hotspotで、parent/pooled map再利用が既にあることと両立する。単なるcache未実装という説明にはしない。avx2_dot_fastは実sampleに現れたが、全headのhardware routing頻度は未記録。FT modeとheadのAVX2 routingは別である。

TTとhistory採点も測定された。通常ordering ownerや独立sortの低いsample数を、ordering全費用ゼロや旧388 sortingの因果的改善量とはしない。合法手生成は残壁がある三局面で約12% selfであり、距離評価と同じcore reachabilityの周辺を共有する。各groupのsource責務を保ったまま比較する。

## 入力別sample・cold固定費とSearch内wall

| 入力 | samples / leaf unknown | Search plain中央値 ms | Search profile ms | profile/plain Search | plain native whole中央値 ms | profile whole ms | profile/plain whole |
| ---- | ---------------------: | --------------------: | ----------------: | -------------------: | --------------------------: | ---------------: | ------------------: |
| high |                 92 / 7 |             928.46096 |         913.63837 |             0.984035 |                    1010.428 |          980.834 |            0.970711 |
| mid  |                114 / 8 |            1138.10907 |        1113.77448 |             0.978618 |                    1214.062 |         1186.054 |            0.976930 |
| low  |                112 / 7 |            1121.10239 |        1109.85387 |             0.989967 |                    1189.595 |         1190.859 |            1.001063 |
| zero |                  2 / 0 |               0.06815 |           0.07245 |             1.063196 |                      87.902 |           69.779 |            0.793829 |

wholeはnative entryからresult publication直前まで。Searchはsession.search呼出全体で、root clone/NNUE prepare/child-buffer/scratch準備を含む。次の`root replay`はSearch外のcanonical prefix準備で、NNUE root prepareの孤立時計ではない。TT/session resetとSearchとnative wholeは内包するscopeなので加算しない。

| profile入力 | model/target setup ms | TT/session reset ms | root replay ms |  Search ms | journal ms | session teardown ms | target drop ms |
| ----------- | --------------------: | ------------------: | -------------: | ---------: | ---------: | ------------------: | -------------: |
| high        |               0.30272 |              32.018 |        0.01699 |  913.63837 |      3.606 |               2.385 |        0.00530 |
| mid         |               0.30061 |              34.756 |        0.05074 | 1113.77448 |      3.798 |               3.251 |        0.00776 |
| low         |               0.28992 |              33.713 |        0.09281 | 1109.85387 |      5.086 |               7.714 |        0.00646 |
| zero        |               0.29571 |              33.469 |        0.14511 |    0.07245 |      3.779 |               2.402 |        0.00751 |

TT1Mの保持は83,886,128B/sessionというnative gaugeで、RSSではない。plain/profile resetは約32〜54ms、zero rootのSearch中央値は0.068msに対してnative whole約88ms。zeroの2 samplesはSHA検証とSearchSession::change_lmrのsetup側だけで、探索関数へのsampleは0。**zero探索の内訳はUNKNOWN**であり、head/FT/BFSのsample無しを無料とは言わない。current fixed cold用途ではsetupの相対負担が大きいが、持続warm sessionへこの比を一般化しない。

profile/plain Search比が高残壁三局面では1未満になった。これは一回のmiddle profileと二つのplainにおける実壁時計変動で、perfが探索を速くすることや負の観測負荷ではない。zeroは約4.3µs差で1.063倍だが短すぎ、setup/allocator/cache/frequency変動も大きい。same-nonclock-workは確認できた一方、observer overheadの非偏推定や厳密な除算補正はできない。新source observerは使っていない。

## 現sourceとの対応と残候補

11.1の説明と同じく、canonical deltaは親validate_accumulator/validate_features、子shape/capacity、checked_positions、matches_positionを経て両view IDをclone_from/remove/insertする。FT32ならrow copyは64f32/256B、pawnは2remove+2add列、wallは2remove+4add列。最後の子finite scanと後のleaf head再validationは別に残る。copyをallocationに読み替えない。4つの現在owner（features.rs/lib.rs/residual.rs/alphabeta.rs）は11.1のSHA・size・modeと全て一致し、source-correspondence.jsonへ固定した。

ResidualScratch/child_buffer/parent map優先・pooled matching child・wall repair/full fallback・399/402のTT先行兄弟準備は現役。通常childはdelta更新の後にgeneric内部TTをprobeする。true goal/third/proof/approxは既に別の早期経路である。trained normalized distanceはfixed distance-logit係数0でもheadへ入力されるため削除不可。

`wall_distance_map_reads/builds/fallbacks`はAIの`publish_distance_counts`が`eval_scratch.distances`から転記するproof/距離scratchのcounterで、features::maps_forのfeature map更新全数ではない。high/midでmap_builds=0でも、sampleに現れるNNUE map repair/BFSが無いという意味にはならない。

今回の同じprofile passのcounterで、内部numeric TT returnへdeltaを延期できる回数Uは0≤U≤min(TT_cutoffs,delta_updates)。root TTも含む保守的上限で、TT_exact_hitsではない。

| 入力 | TT exact hits | TT numeric cutoffs | delta更新 | 省略回数上限/delta % |
| ---- | ------------: | -----------------: | --------: | -------------------: |
| high |            20 |              2,109 |   999,995 |               0.2109 |
| mid  |            53 |             14,939 |   990,013 |               1.5090 |
| low  |            37 |             10,223 |   928,816 |               1.1006 |
| zero |             7 |                  0 |         4 |               0.0000 |

この3つの大きい探索でも上限は0.21〜1.51%で、generic TTを先に置けばCPUの同じ割合が省けるとは言えない。各更新の費用、root/internalやwindow/depth/context/typed-kindの分解は残る。新observerや別TT/delta集計campaignは不要で、今回のcounterを補助判断へ統合した。元A8 snapshotとwhole、sole RNG/CIは再集計していない。

| 優先する検討                                      | 今回の根拠                                              | 安全性・保守費／未確定                                                                                                                                                                                                   |
| ------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| head packing/validation/FT準備を同じowner内で精査 | head17.5%、validation10%、delta owner8.44% selfが実観測 | 割合を足して除去可能量にしない。public任意Features/shape/nonfinite/model拒否、FP32順序・overflow routing・scaler/STM・Err/undoを保つ。借用scratchは既にある。private制御フローで検査重複を整理できるかが候補で、採用なし |
| 現在のmap repair/BFSの費用対効果                  | wall-distance15%、mid/lowでは16.7/18.75% self           | 既存parent/pooled map hitを壊さず、391の有効再利用を二重実装しない。393/398の撤去実装を復活しない。孤立BFS呼出数/辺訪問・repair成功率はUNKNOWN、表やcache追加は別の判断                                                  |
| 合法手生成・history採点の局所責務                 | 合法生成11.875%、history採点3.75% self                  | 合法集合・fullhistory・goal/cancel・順序/tie・PVS/TTを維持。新solver/別ordering/キャッシュをこの結果だけで採用しない                                                                                                     |
| TT-before-delta案は後順位                         | TT本体等5% self、更新省略回数上限0.21〜1.51%            | TTコスト全体の除去案ではない。same depth/context/closing bound/legal bestとroot/proof/approx除外、common enter/undo/errorを一回に保つ必要があり保守費が高い。費用上限の追加証拠なくsource変更へ進めない                  |

旧390のmaps14.43/validation4.74/head11.13等と今回の数値は、model/TT/LMR/P、root・stop・sample数、clock/cold条件、source版が違う。差分を改善率・Cedar一般CPU比・棋力/LMR判断へ利用しない。4局面のnode-limited finite hotspot優先度であり、残壁による一般的因果やデフォルト変更を意味しない。

## custody・失敗・費用・終了

実execution sequence STOP 2026-10-18T14:16:56.384147+00:00、outerSTOP 2026-10-18T14:16:56.437205+00:00。actual outer 62.467930802sは内側のnative/guardian/sequence/collection clockを内包するので加算しない。別の二つのpre-native失敗はCLI --settings/--intentとsequence cwd不足で、exit2/exit1、0 native/0 Search。原config/result/captureはimmutableのまま、具体API照合後の同じ未入場12だけを新lifetimeで実行した。unused import lint、空sample parser、preprofile TMP assembly、報告rendererの構文/unused importと最終source locator照合（存在しない関数名・誤ったowner）の失敗とreturned NULL対disk mask/persistも保持した。単なる成功exitをD8達成やmodel408の新資格にしない。

native manifest/runtime/parent復元と精確PID/start/bootのfreshabsence、maintained direct wait/reap/handles/TMPはcollection-v1/native-STOP.jsonおよび最終STOPへ束縛。profile時の直接wait対象はperfで、別のnative wait receiptを捏造しない。全native/profilerの停止は別途fresh確認した。通知だけのsupervisorは科学childと区別する。

新whole32MiB/support21839fd2は一度、RAW4本・設定/journal/result・TMP/FAILED・この解析を同じscopeで保持する。model/image/libraryコピー0、旧8/9/10 supportの再apply/借用/refund0。CPU2/G0/family4GiB incl64MiB/G0/host4GiBの実normal admissionを使い、解析は別CPU0/G18の短いfamily512MiB管理共有phase。普通authorityはDolt実需要に対する別1GiB phase。全host/futurequietは主張しない。保持量は最後にOWN一回だけ確認し、global actual、physical NN、isolated BFS/FT/copy、continuous peak/full feesはUNKNOWN。

関連成果: [collection](../../../../.worktree/assets/perf/cedar-evaluation-preparation-v1/current-profile-v1/collection-v1/result.json)、[aggregate profile](../../../../.worktree/assets/perf/cedar-evaluation-preparation-v1/current-profile-v1/collection-v1/aggregate-profile.json)、[groups CSV](../../../../.worktree/assets/perf/cedar-evaluation-preparation-v1/current-profile-v1/collection-v1/groups.csv)、[native STOP](../../../../.worktree/assets/perf/cedar-evaluation-preparation-v1/current-profile-v1/collection-v1/native-STOP.json)、[frozen plan](../../../../.worktree/assets/perf/cedar-evaluation-preparation-v1/current-profile-v1/profile-plan.json)。Main/Git/Cargo/source算法・model/features/math/default/product/generatorは変更せず、USERPAUSE323/342.17/seals/newE/oldfits96/元RAWFAILEDを保持する。追加call/refill/新対局/fit/観測framework/旧RAW再parse0。
