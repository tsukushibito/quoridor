# 固定12分岐：原参照と記録された判断

A=fixed_one、B=depth_rank。同じ開始fullhistoryと全共有着手prefixを照合した最初の分岐。plyは0始まりの絶対ply、game/RAW行は元dataset内番号。ActionID/PVは元記録の整数。valueは手番視点の選択的推定でoracleではない。

二色score=1/0の各群で既存ID順先頭3をRAW抽出前に固定した。12例とも分岐し、補充0。結果を使った説明用選択であり、全例prefix4に偏る。TT/killer/history/時計/先行探索状態の同一性、枝のrank/実q/静的値はUNKNOWNまたは未記録。

## 固定D family 1／B両勝ち／ply 4

共有局面：P0/P1座標=`[[3,1],[4,7]]`、stocks=`[10,9]`、配置wall ActionIDs=`[150]`、手番P0。共有着手=`[3,150,12,67]`。fullhistory action prefix SHA256=`19edaacbf9c3fcfb6f1086ed832294df742bdbe256c0a48635dc5e6d065f4bd5`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits | PV           | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | ---------------------- | ------------ | ------------------------------------------------- |
| A    |     84 |      `4` | `0.0` / `"00000000"`   | `[84,58,21]` | 83764 / 1395-6-0 / 10                             |
| B    |     83 |      `4` | `0.0` / `"00000000"`   | `[83,58]`    | 111850 / 1988-48-0 / 13                           |

A: game 1、stop=`internal_time_limit`、selection=`completed_iteration`、caller 98.967ms、receipt slack 20.219ms、receipt→terminal 19.140ms。実続行先頭8=`[84,91,94,156,149,154,11,105]`、実goal勝者P1、終局ply 66。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行2、非圧縮byte offset 228496、行SHA256=`cc0226afac81e13649965e0e6ccd50e95e9f7ff92921ce2e257a8504ca174e2b`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

B: game 0、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.512ms、receipt slack 37.394ms、receipt→terminal 36.873ms。実続行先頭8=`[83,91,85,58,87,49,81,40]`、実goal勝者P0、終局ply 67。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行1、非圧縮byte offset 0、行SHA256=`6d62a8df137964fcc621bda527466a65d693621f6307f64b68f6b1550c7ebb8d`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

## 固定D family 3／B両負け／ply 6

共有局面：P0/P1座標=`[[4,1],[3,7]]`、stocks=`[8,9]`、配置wall ActionIDs=`[104,158,190]`、手番P0。共有着手=`[158,104,190,75,13,66]`。fullhistory action prefix SHA256=`283f94852306090f4a7c0ed3b612534b315b224d4d0f0fe2dce1e2dda850473a`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits | PV           | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | ---------------------- | ------------ | ------------------------------------------------- |
| A    |     83 |      `4` | `0.0` / `"00000000"`   | `[83,57,85]` | 88499 / 716-64-1 / 7                              |
| B    |     22 |      `4` | `0.0` / `"00000000"`   | `[22,57]`    | 208676 / 8005-37-0 / 5                            |

A: game 5、stop=`internal_time_limit`、selection=`completed_iteration`、caller 101.301ms、receipt slack 39.852ms、receipt→terminal 41.085ms。実続行先頭8=`[83,101,85,99,81,137,127,110]`、実goal勝者P0、終局ply 65。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行6、非圧縮byte offset 1034976、行SHA256=`32077eb78ad81197c664a4ee55e45372f4f84005d0f421ef538ab04165c1cc08`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

B: game 4、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.230ms、receipt slack 68.337ms、receipt→terminal 67.522ms。実続行先頭8=`[22,57,31,48,83,140,40,142]`、実goal勝者P1、終局ply 50。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行5、非圧縮byte offset 867331、行SHA256=`8b153083e1ffd7fcb9aabbdde8e4b0bc9282dc35e0e57aa23e07769e52045048`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

## 固定D family 5／B両勝ち／ply 5

共有局面：P0/P1座標=`[[3,1],[5,8]]`、stocks=`[9,9]`、配置wall ActionIDs=`[125,166]`、手番P1。共有着手=`[166,125,3,77,12]`。fullhistory action prefix SHA256=`c0a1acf5c095b923244d568913da1321e6abb5c85e28fcbe75d203ca73829684`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits       | PV         | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | ---------------------------- | ---------- | ------------------------------------------------- |
| A    |    121 |      `4` | `-0.09966802` / `"bf1eccbd"` | `[121,21]` | 108075 / 2680-49-1 / 15                           |
| B    |    131 |      `4` | `-0.19737531` / `"c11c4abe"` | `[131,21]` | 108115 / 1295-36-0 / 15                           |

A: game 6、stop=`internal_time_limit`、selection=`completed_iteration`、caller 98.967ms、receipt slack 40.959ms、receipt→terminal 39.873ms。実続行先頭8=`[121,141,198,187,92,88,148,127]`、実goal勝者P0、終局ply 67。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行7、非圧縮byte offset 1256561、行SHA256=`cea60db6f0123462b11e37b5c8eff93ef8d1d4ef48c982e745551bfb911bb51d`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

B: game 7、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.066ms、receipt slack 40.205ms、receipt→terminal 39.229ms。実続行先頭8=`[131,142,155,127,92,3,98,140]`、実goal勝者P1、終局ply 60。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行8、非圧縮byte offset 1485293、行SHA256=`c0f9d8606658802b49260ce120054ad1f0087ae1d2b53f2dc0356e6b8d6c9259`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

## 固定D family 7／B両勝ち／ply 9

共有局面：P0/P1座標=`[[3,1],[5,8]]`、stocks=`[7,7]`、配置wall ActionIDs=`[88,91,93,110,137,177]`、手番P1。共有着手=`[110,177,137,77,13,93,12,91,88]`。fullhistory action prefix SHA256=`8741dc365913a6f177a7415b51e3bb74f3df3bf3b65771977d65d53676dafd04`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits      | PV             | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | --------------------------- | -------------- | ------------------------------------------------- |
| A    |    156 |      `5` | `0.09966802` / `"bf1ecc3d"` | `[156,86,147]` | 135638 / 11440-86-0 / 12                          |
| B    |    146 |      `4` | `0.0` / `"00000000"`        | `[146,86,156]` | 189586 / 7456-1-0 / 10                            |

A: game 10、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.455ms、receipt slack 8.809ms、receipt→terminal 8.127ms。実続行先頭8=`[156,86,147,3,112,89,68,197]`、実goal勝者P0、終局ply 57。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行11、非圧縮byte offset 2059304、行SHA256=`12aff041073168b0109f4ae79708e7999cb5b079dc4a7e1d21e0f4d945a6e575`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

B: game 11、stop=`internal_time_limit`、selection=`completed_iteration`、caller 100.138ms、receipt slack 71.778ms、receipt→terminal 71.867ms。実続行先頭8=`[146,86,156,3,68,89,59,4]`、実goal勝者P1、終局ply 66。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行12、非圧縮byte offset 2252073、行SHA256=`60f51ecbdfd83f66de80fe4a76e53d3d0ec1465f1e3d12d40740dd5663d5eb23`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

## 固定D family 20／B両負け／ply 4

共有局面：P0/P1座標=`[[3,0],[4,8]]`、stocks=`[9,8]`、配置wall ActionIDs=`[156,170,196]`、手番P0。共有着手=`[170,196,3,156]`。fullhistory action prefix SHA256=`7e5e13748a2ac06d6a2a52531eb81ca07702f19427ba57b7fe6450860460ee61`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits | PV               | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | ---------------------- | ---------------- | ------------------------------------------------- |
| A    |     85 |      `4` | `0.0` / `"00000000"`   | `[85,107]`       | 80809 / 2164-20-0 / 11                            |
| B    |    125 |      `4` | `0.0` / `"00000000"`   | `[125,89,87,75]` | 115719 / 2562-15-0 / 12                           |

A: game 28、stop=`internal_time_limit`、selection=`completed_iteration`、caller 98.691ms、receipt slack 26.005ms、receipt→terminal 24.655ms。実続行先頭8=`[85,83,125,146,4,87,81,134]`、実goal勝者P0、終局ply 61。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行29、非圧縮byte offset 6023981、行SHA256=`9a146f66367c4d34dd096d9c2c0b4ce5ae12082331ebc6985c62e1e5a9bf82f6`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

B: game 29、stop=`internal_time_limit`、selection=`completed_iteration`、caller 101.532ms、receipt slack 39.726ms、receipt→terminal 41.212ms。実続行先頭8=`[125,91,202,85,4,135,81,105]`、実goal勝者P1、終局ply 42。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行30、非圧縮byte offset 6230877、行SHA256=`fcbb19d4f2678ffcaa8cfdbaa7460f8a3b5f094a0657b8f4eaf3baabb368b9f3`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

## 固定D family 21／B両負け／ply 6

共有局面：P0/P1座標=`[[4,2],[4,7]]`、stocks=`[9,8]`、配置wall ActionIDs=`[84,133,166]`、手番P0。共有着手=`[166,133,13,84,22,67]`。fullhistory action prefix SHA256=`91fc294fc6f539fd0c22d84b06be65128113e359b68689bab4ec87a3680f72dc`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits      | PV                    | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | --------------------------- | --------------------- | ------------------------------------------------- |
| A    |    196 |      `5` | `0.29131263` / `"ee26953e"` | `[196,100,198,76,21]` | 153066 / 13901-66-1 / 11                          |
| B    |     31 |      `4` | `0.19737531` / `"c11c4a3e"` | `[31,139]`            | 186335 / 5240-61-0 / 10                           |

A: game 31、stop=`internal_time_limit`、selection=`completed_iteration`、caller 98.979ms、receipt slack 28.008ms、receipt→terminal 26.933ms。実続行先頭8=`[196,100,140,198,86,68,88,163]`、実goal勝者P0、終局ply 49。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行32、非圧縮byte offset 6566948、行SHA256=`4dc88c6c8ab5fedd73360efd9823d2d1590c90176d2a83264adf291011393877`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

B: game 30、stop=`internal_time_limit`、selection=`completed_iteration`、caller 101.177ms、receipt slack 72.500ms、receipt→terminal 73.631ms。実続行先頭8=`[31,108,100,171,111,66,131,204]`、実goal勝者P1、終局ply 58。

RAW: [batch-001/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-001/data/completed.jsonl.gz) 行31、非圧縮byte offset 6370192、行SHA256=`26751fffca52f068f31872cf419a19ba3df84dad7142ca6c00706fa55144627f`。archive SHA256=`4f05eb76238674d5dad3c685ec17cb89c7788aed791af6f5c108158f5ee48dec`。

## NNUE family 1／B両勝ち／ply 4

共有局面：P0/P1座標=`[[3,1],[4,7]]`、stocks=`[10,9]`、配置wall ActionIDs=`[150]`、手番P0。共有着手=`[3,150,12,67]`。fullhistory action prefix SHA256=`19edaacbf9c3fcfb6f1086ed832294df742bdbe256c0a48635dc5e6d065f4bd5`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits      | PV            | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | --------------------------- | ------------- | ------------------------------------------------- |
| A    |     97 |      `4` | `0.16015062` / `"86fe233e"` | `[97,58,104]` | 60332 / 372-0-0 / 46                              |
| B    |     21 |      `3` | `0.79776216` / `"243a4c3f"` | `[21,58,30]`  | 58335 / 336-0-0 / 40                              |

A: game 1、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.696ms、receipt slack 5.918ms、receipt→terminal 5.565ms。実続行先頭8=`[97,58,168,200,100,128,151,207]`、実goal勝者P1、終局ply 56。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行2、非圧縮byte offset 171093、行SHA256=`209003c1ab43868f843fe523afddff7469777806d987bd84da62635cc3b0e62b`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

B: game 0、stop=`internal_time_limit`、selection=`completed_iteration`、caller 100.177ms、receipt slack 55.803ms、receipt→terminal 55.936ms。実続行先頭8=`[21,58,30,154,39,49,100,200]`、実goal勝者P0、終局ply 51。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行1、非圧縮byte offset 0、行SHA256=`fdb4ab8704ae51774d7b58d02a1e4c96172c15c1e0a77478c4b5cd49a72da32b`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

## NNUE family 2／B両勝ち／ply 6

共有局面：P0/P1座標=`[[5,2],[4,7]]`、stocks=`[10,8]`、配置wall ActionIDs=`[87,201]`、手番P0。共有着手=`[13,67,14,201,23,87]`。fullhistory action prefix SHA256=`efbe57106c3f88e5e60edb0c7bd8ab5a082c1ccfd3e2ddd59e911412811d9db1`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits      | PV                  | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | --------------------------- | ------------------- | ------------------------------------------------- |
| A    |    157 |      `4` | `0.27488044` / `"21bd8c3e"` | `[157,116,152,122]` | 77120 / 1564-19-1 / 57                            |
| B    |    152 |      `4` | `0.07270763` / `"bde7943d"` | `[152,122]`         | 80918 / 753-9-1 / 39                              |

A: game 2、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.631ms、receipt slack 28.526ms、receipt→terminal 28.102ms。実続行先頭8=`[157,170,148,192,133,66,100,102]`、実goal勝者P1、終局ply 56。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行3、非圧縮byte offset 359905、行SHA256=`bf06813f20502dfd63c00e958fc6465644f13727cdc0a16109b76eae43e7b5b4`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

B: game 3、stop=`internal_time_limit`、selection=`completed_iteration`、caller 101.385ms、receipt slack 24.483ms、receipt→terminal 25.817ms。実続行先頭8=`[152,197,157,141,32,58,164,49]`、実goal勝者P0、終局ply 63。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行4、非圧縮byte offset 548972、行SHA256=`a9ce93a9c159f0f06efac4cfc40c3482ccf7b161fae90a97cc8854ae7bfaa597`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

## NNUE family 5／B両勝ち／ply 4

共有局面：P0/P1座標=`[[3,0],[5,8]]`、stocks=`[9,9]`、配置wall ActionIDs=`[125,166]`、手番P0。共有着手=`[166,125,3,77]`。fullhistory action prefix SHA256=`73e3cb5b24366f0f7abd60484456708c992c2eacc09dcbfd69d734c1748ff8d3`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits     | PV              | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | -------------------------- | --------------- | ------------------------------------------------- |
| A    |      2 |        — | — / —                      | `[]`            | 0 / 0-0-0 / 0                                     |
| B    |    145 |      `3` | `0.5197491` / `"470e053f"` | `[145,182,164]` | 50694 / 105-0-0 / 22                              |

A: game 7、stop=`cancelled`、selection=`legal_fallback_no_completed_iteration`、caller 105.143ms、receipt slack 4.921ms、receipt→terminal 10.012ms。実続行先頭8=`[2,90,103,116,88,68,109,201]`、実goal勝者P1、終局ply 60。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行8、非圧縮byte offset 1255015、行SHA256=`8b133369a1ba6eaf686e8d5f332535908b27c1234b761964dda847f4592bdde6`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

B: game 6、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.725ms、receipt slack 53.885ms、receipt→terminal 53.571ms。実続行先頭8=`[145,116,118,114,88,203,97,121]`、実goal勝者P0、終局ply 49。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行7、非圧縮byte offset 1091055、行SHA256=`70f244d33c405ce2cd4da8769f6e36d5fc2e992784a00695b1e40d6584b61671`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

Aは完成snapshotなしの合法fallback。記録terminal nodes=0/trial=0を、物理Search/forwardが無かった証明やLMRの悪手原因へ変換しない。初回準備・制御・schedulingの原因は未分離。原勝敗・分母から除外しない。

## NNUE family 8／B両負け／ply 9

共有局面：P0/P1座標=`[[4,2],[4,6]]`、stocks=`[9,10]`、配置wall ActionIDs=`[97]`、手番P1。共有着手=`[13,77,4,76,97,67,13,58,22]`。fullhistory action prefix SHA256=`6fc6567887a8926f0b144b2b236bcea75afe24bc334a977991b3c0a6b347947f`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits       | PV                 | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | ---------------------------- | ------------------ | ------------------------------------------------- |
| A    |     49 |      `4` | `-0.20218581` / `"cc094fbe"` | `[49,81,208,201]`  | 76488 / 1276-16-5 / 67                            |
| B    |    208 |      `4` | `-0.4735467` / `"b774f2be"`  | `[208,31,121,148]` | 82002 / 678-3-0 / 82                              |

A: game 13、stop=`internal_time_limit`、selection=`completed_iteration`、caller 100.318ms、receipt slack 28.179ms、receipt→terminal 28.446ms。実続行先頭8=`[49,31,125,109,208,131,202,112]`、実goal勝者P1、終局ply 44。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行14、非圧縮byte offset 2398655、行SHA256=`11bd15d80df904d4ae5624dc7d13ee5fbdd1df4114daaeb5af116f638fd367ef`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

B: game 12、stop=`internal_time_limit`、selection=`completed_iteration`、caller 100.108ms、receipt slack 16.508ms、receipt→terminal 16.566ms。実続行先頭8=`[208,88,202,31,128,153,141,146]`、実goal勝者P0、終局ply 65。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行13、非圧縮byte offset 2177710、行SHA256=`f543b002883f81e085c8e0525869bf6cbc9b4a074943433a7feca179f613335b`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

## NNUE family 12／B両負け／ply 8

共有局面：P0/P1座標=`[[3,3],[2,7]]`、stocks=`[10,9]`、配置wall ActionIDs=`[121]`、手番P0。共有着手=`[3,75,12,74,21,65,30,121]`。fullhistory action prefix SHA256=`ee7690e1b9c3c1d83e9ff5225df4fbcb3ba2eaf56411b243a17e6511d0635c4b`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits       | PV                | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | ---------------------------- | ----------------- | ------------------------------------------------- |
| A    |    123 |      `4` | `0.08794684` / `"791db43d"`  | `[123,133]`       | 77331 / 1116-13-2 / 57                            |
| B    |     39 |      `4` | `0.075440235` / `"69809a3d"` | `[39,56,194,137]` | 78878 / 463-9-0 / 67                              |

A: game 20、stop=`internal_time_limit`、selection=`completed_iteration`、caller 100.010ms、receipt slack 23.466ms、receipt→terminal 23.428ms。実続行先頭8=`[123,66,151,207,196,125,112,186]`、実goal勝者P0、終局ply 73。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行21、非圧縮byte offset 3553316、行SHA256=`18c341dfe03531ad4f24a5a55e00385915a9511e3c8c083a13412e69abb13637`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

B: game 21、stop=`internal_time_limit`、selection=`completed_iteration`、caller 102.732ms、receipt slack 21.214ms、receipt→terminal 23.889ms。実続行先頭8=`[39,56,48,201,57,131,145,47]`、実goal勝者P1、終局ply 62。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行22、非圧縮byte offset 3802840、行SHA256=`ceec687f57944e4edc44425d4d14980c8c461fc3e3a36608175c00e19d8ea481`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

## NNUE family 20／B両負け／ply 4

共有局面：P0/P1座標=`[[3,0],[4,8]]`、stocks=`[9,8]`、配置wall ActionIDs=`[156,170,196]`、手番P0。共有着手=`[170,196,3,156]`。fullhistory action prefix SHA256=`7e5e13748a2ac06d6a2a52531eb81ca07702f19427ba57b7fe6450860460ee61`。開始root_key/countsと全fieldは[examples.json](examples.json)の同familyを参照。

| 方法 | action | 完成深さ | value STM／f32 LE bits     | PV            | terminal nodes／LMR trial-confirm-fullwindow／PVS |
| ---- | -----: | -------: | -------------------------- | ------------- | ------------------------------------------------- |
| A    |    168 |      `4` | `0.5247698` / `"5057063f"` | `[168,128]`   | 59235 / 793-0-0 / 61                              |
| B    |     97 |      `3` | `0.8076102` / `"8bbf4e3f"` | `[97,83,194]` | 54672 / 501-0-0 / 62                              |

A: game 28、stop=`internal_time_limit`、selection=`completed_iteration`、caller 100.593ms、receipt slack 9.333ms、receipt→terminal 9.848ms。実続行先頭8=`[168,125,153,202,165,77,2,78]`、実goal勝者P0、終局ply 67。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行29、非圧縮byte offset 5171850、行SHA256=`085318c69e7ee377843a9ac38abbb4016154a4d54d895040392043cec5ec00bb`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

B: game 29、stop=`internal_time_limit`、selection=`completed_iteration`、caller 99.677ms、receipt slack 51.490ms、receipt→terminal 51.126ms。実続行先頭8=`[97,67,12,201,166,99,149,205]`、実goal勝者P1、終局ply 56。

RAW: [batch-000/completed.jsonl.gz](/workspaces/quoridor/.worktree/assets/perf/lmr-standard412-arena392-v1/batch-000/data/completed.jsonl.gz) 行30、非圧縮byte offset 5399962、行SHA256=`86f99b8dc7b35c5e16af98fb67f5e4881041221851b125e6386b6355e88d1896`。archive SHA256=`634a0037fcb84cd6529d6fe91b77b0b5ec5148ea352b3e4403f43dbb6788f70b`。

各行のselected/terminal work、TT、全clock、完全開始履歴、直接RAW参照は[examples.json](examples.json)に保持。実勝者はその一手の正しさを証明せず、異PV/valueを単独LMR演算の効果へ帰属しない。
