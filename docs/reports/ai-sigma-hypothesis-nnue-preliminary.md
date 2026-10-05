# NNUE予備調査：教師の区別と距離更新の次診断

quoridor-4lc.154では、保存済み教師候補は有限に取り出せる一方、NNUEの313特徴・差分評価・学習export・holdout分離は未整備と判断した。次案は最大1つ、既4合法prefixを使う**壁不変のgoal-distance-map再利用と固定座標疎特徴の総費用診断**を選ぶ。教師schemaだけの追加確認より、特徴生成と合法手の費用がNNUE＋αβ試作の選定を変えるかを先に測る。今回その診断を実装・実行していない。NNUEの速度・棋力優位は未測定。

新研究目標・NNUE方針・チーム設計の正本3pathを読んだ。Sigma忠実探索は基準・教師・評価基盤の段階、自前PV学習とNNUE＋αβの棋力比較は別の未完了段階である。151のStageB完了や自前PV完成を予備調査のgateにしていない。313入力、距離2値、量子化は候補で、採用済み固定仕様ではない。外部一次資料を新たに取得せず、以下はローカルsource・保存schemaの根拠に限定する。

## 保存教師の有限確認

読取前に151 StageA-r2のfixedSigma reference/K32をinitial-p1、asym-hv-p2、frame10-prefix-13、frame10-prefix-14の最大4rootへ固定した。rawの他row・深部はJSON境界をskipし、選定rootのCPと最初のNN recordだけを解釈した。rawを複製・展開していない。原raw SHA `d37215cbc7914519ca24ab254c5e413d21e780389094faed537280a059c234d2` は前後一致し151分析のbindingと一致、input SHAは `dc205f8d7e00ee52aca51845ddbca5e3085d0aebdb22c3f4ceb6fa139cd10954`。

| fixed root | 手番0=P1/1=P2 | root NN値（手番視点） | rootmean（手番視点） | root N |
| --- | ---: | ---: | ---: | ---: |
| initial-p1 | 0 | .214375 | .192492 | 32 |
| asym-hv-p2 | 1 | −.407375 | +.295971 | 32 |
| frame10-prefix-13 | 1 | .793808 | .502360 | 32 |
| frame10-prefix-14 | 1 | .472545 | .402073 | 32 |

4/4でroot path=[]、key/history/ply/turnと648 features bitsを保存し、fixture特徴とroot特徴がbit一致、rootmean=valueSum/Nの保存算術も一致した。4件ともNN32/terminal-noNN0。このNを一般にNN回数と同一視しない。StageA検索なのでgame outcomeは4/4欠測。全fixtureは保存classificationがlegal-replayで合法prefixを持つが、今回再replayによる合法性認証は行っていない。最初2件は完全board/壁remainingがあり、後2件のboardはtotal_plyのみで、完全stateの再構成には合法prefixが必要。未保存boardを補完してteacher-readyとは呼ばない。

保存model-loadは両engineの同digest `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d` を報告する。これは保存bindingで、148/154が新たにモデルをload又は独立hashしたものではない。actual-served-sourceと151 config/provenanceへの参照を自己dataに残す。現在読んだsourceのhashと原実測全版の同一性は別に扱う。

教師は次を混ぜない。

- **leaf NN値**はそのleaf状態の手番視点のモデル評価。rootの最初NN値はroot状態のモデル値であり、深部leaf値をrootへ無条件に付けない。モデル蒸留には使えるが探索の改善を直接教師にしていない。
- **探索rootmean**は指定教師model/source/予算・探索政策が集めた平均backup値。151 sourceはleaf側から親へ1edgeごと符号を反転し、nodeSum/nodeNを出力する。P1固定出力ならturn=1で符号反転する。asym-hv-p2でNNとrootmeanの符号が逆なので、二つを同一targetへ混ぜると意味が変わる。小試作の主target候補は保存rootmeanとし、root NN値を別列に残す。K32の質や深い探索の正解を保証しない。
- **visits**はその探索のAction配分で、NNUE value targetではない。root edge Qは子側符号や未訪問を区別する必要があり、真parentmeanの代用品にしない。
- **game結果**は実継続policy・時計・失敗に依存する終局target。固定P1 winnerから各局面手番へ変換し、正常terminalとtyped faultを分ける。今回4rootには結果がないので0/drawや同prefixの別run結果で埋めない。

教師行にはrules/source/model/binary、検索予算、root/leaf種別、視点、合法prefix、完全board又は再構成根拠、wallremaining、history_counts、totalply、NN/backup/terminal-noNNの分母を残す。313＋距離は履歴を表現しないため、同盤面でもrepetition合法手や200ply drawの違うtargetが同入力へ合流し得る。教師metadataとTTにはその違いを保持し、terminalをネット評価の前に処理する。必要なら安いcontext特徴を後段に足すか、その教師の射程を限定する。いずれもまだ採用していない。

学習とholdoutは行単位のランダム分割ではなく、元prefix・同game/色交換pair・対称変換・同state合流を同じfamilyへまとめて分ける。既診断局面はschema確認とtrain候補で、独立評価holdoutへ流用しない。教師model固定、教師の深さ/予算別target、初期重みか継続学習かを記録する。loss・教師一致を棋力や汎化の証拠にしない。

## 特徴・距離・履歴のsource根拠

`crates/quoridor-core/src/research.rs:350` の現648特徴は毎callでgoal8/0の81マスmulti-source BFSを2回計算し、P2では上下反転・own/other入替を行う。`position.rs:161` のwall_distanceも壁だけのグラフを使い、駒は障害として扱わない。したがって壁不変ならgoal-mapは駒・手番・履歴・残壁数に依存せず再利用できる。距離は駒jumpや将来壁配置を含む実勝利手数ではない。

NNUE候補313=81×2+64×2+11×2+1は固定座標・固定playerで、通常pawn手の変更は駒old/new＋binary手番の最大3entry、壁手は壁1＋remaining-onehot old/new＋手番の最大4entryとなる。hidden幅Hなら第一層の更新はこれらentryの重みvector更新費用を持つ。入力次元313だけから速度を推定しない。壁mapを第一層へ密に入れると壁1手で多数距離entryが変わる一方、少数距離を後段へ入れればwall-map費用と疎更新を分離できる。駒×壁の相互特徴は駒移動で多数active入力が変わり得る。合法壁・代替経路・壁1枚効果も、生成と更新の費用・学習上の利益を別に測る必要がある。

wall-only cache keyはgraph/rules版＋H64＋V64＋goal row（固定9×9）。goal8/0のmapをimmutableで保持し、壁変更では別map、unmakeでは親handleへ戻す。別枝の親mapを上書きしない。同じ距離scalarだから全81mapが同じ、という省略はしない。2枚u8 mapのpayloadは162B、256組で41,472Bだが、hash table・所有・eviction等のoverheadは別である。

history・pawns・壁remaining・手番は**distance map**から分離できるが、合法手cache/teacher signature/TT値・boundのキーから落とせない。research `SigmaContext` は同history key再訪を考慮した合法手と200ply/no-legal drawを持つ。他方standard `Game` は自動ply drawなしである。αβを通常Gameへ接続するだけでは同教師rulesにならない。terminal/history、合法手列、make/unmake、TT key構築とアクセス、cache map、特徴、NNUE更新、後段推論、探索/確定までが総費用であり、現時点でαβ/TT/NNUE実コストは未測定。

## 最大1次案と結果別の判断

次案は自己private領域の**distance-cache＋疎特徴コスト診断**。単独writer候補はexperiment、shared crates/models/151原sourceはreadonly。既4prefixだけ、保存済み順に各rootから最初8pawn/最初8wall（存在する範囲、計最大16action）を結果前固定し、同合法手列でuncached2BFSとimmutable-map cacheを比較する。最初に全81map/距離、合法集合、313 full encode対delta、unmake復帰を照合する。jump/diagonal、wall invalidation、hit/miss/eviction、同walls・異pawns/side/history、draw/goalを必要mockに含める。合法性の代わりに距離が良さそうな枝を使わない。

正しさ1巡、warm1巡、各variant固定64反復、input登録順のAB/BAを交互にし、cold/warmと順を分ける。BFS・合法手/到達確認・feature full/delta・cache lookup/hash/copy・make/unmake・context/TT key構築の別時間と合計、cache bytesと変更entry数を残す。今回64反復やcacheを実行していない。JS browserで測ればこのplumbing/アルゴリズムの診断であり、Rust/Wasm NNUE速度やαβのTT利用を代弁しない。

将来見積りはwriter20分、static総120秒、NN0 browser各30秒/累計60秒、少数独立保存確認10分。静的CPU0・browser CPU2各単1、RAM/Chrome temp/新scope保存は親残資源でcoordinatorが別配分する。親期限が早ければ縮小や延長ではなく未完了を返す。学習・モデルload・新教師NN・game・GPU0を前提とし、今回154の許可をこの実行へ読み替えない。

全inputで総費用が下がりparity/保存上限を満たせば、小NNUE evaluator＋αβ private skeletonへ次配分する根拠になる。parity不一致なら最適化枝を止め正しいuncachedを保持し、key/history/復帰の原因を修復する。混在・利益なしなら一般cache拡大を止め、小さい親map又はuncachedを保持する。合法壁BFSやmake/unmake/key費が支配すればその実測部を次実装対象へ変える。入力/版不足なら補充せず未解決。NNUE人工重みparityやteacher bulk exportも有効な競合だが、今回は自動追加しない。native/Wasm、CPU/GPU、短中長持ち時間の棋力判定は後段で別に行う。

## 実施・保存の限界

受領01:53:50.576807UTC、本人割当・ready/show goal+self・pauseなしを確認して154のみclaim、開始報告を配送した。静的schema-r1は最大4rootの保存算術・field存在を確認し成功。NN/Chrome/model/build/game/学習/取得/委譲0。管理r0の並行出力混在、存在しない2pathのrg失敗、速報dispatch競合は失敗のまま保持し、管理lockと独立output名で修復、dispatchを有界再試行した。科学的負例へ変換していない。

旧保守11,560,048Bを減額せず、148保持＋Git forecast841,527Bを保守加算し、新154最大1MiBを足すcombined forecastは13,450,151B<14MiB。親追加予約0。原raw全copy/展開0。自己command ledger/源hash/結果/欠測/停止・Git stream復元・backupを保存してcoordinator受入れへ渡す。現在identity不在とowned waitの自然終了、全host/全期間保証を分ける。処理02:13:50.576807、新command02:10:50.576807、提出02:23:50.576807の早側期限を維持し、151の後着でresetしない。goal/他者close、actualgo・最強・Sigma/NI・政策採用認定0。
