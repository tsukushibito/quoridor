# 175 native epoch2 保存結果の独立裁定

2026-10-03 critic。契約c08106c22fc19d13ebaeca573b88deec612a921a、受領07:56:53 UTC、ready/show goal+self・pauseなし・本人割当を確認して07:57:21.940755 claim/静的実開始、統括へ配送。新科学/NN/対局/model/Chrome/build/GPU/取得/委譲0。writerは175自域と本報告のみ。08:02新検算終了、08:05処理、08:10提出の早側を固定した。

**「不確か」を支持する。非劣性も実用上劣性も今回の事前規則では支持されない。** この結論はepoch2登録済33block/99pair/198gameに限定する。旧epoch1や未登録future1002gameをwealthへ混合していない。Sigma同等・最高棋力、600pair完了の認定ではない。

## 独立算術と分母

原blocks.jsonlの全33行から各blockの3core/3pair/6slotを再算した。core[2,4,6]、pair順、候補の両色、game ID一意、登録順33行を照合。198終局はGOAL、候補95勝/0分/103敗、品質未知0、登録済品質平均は95/198=0.47979798。運用品質の未知を除外したcomplete-only成績ではなく、今回の登録済分母が全て点値になった結果である。

6gameの半点得点合計kからY=k/12、lambda=a/4とし、NIの5積を整数で更新した。因子は(240+a(5k−27))/240、a={1,2,4,6,8}。各prefixでsum P ≥100×240^nを確認した。劣性はa={1,2,4,6}、因子(240−a(5k−27))/240、sum Q ≥80×240^nを確認した。owner集計器を実行せず、独自Python整数/Fractionで全33prefixの正確な分子・分母を保存し、ownerの保存値とも一致した。

| 項目 | 独立結果 |
| --- | ---: |
| NI最終wealth | 1.8850575878116762 |
| 劣性最終wealth | 0.43847935098694685 |
| 最初のNI閾値20到達 | 全33prefixでなし |
| 最初の劣性閾値20到達 | 全33prefixでなし |
| 登録済品質未知 | 0/198 |
| 未登録future | 1002/1200 capacity |

両方向はそれぞれ片側5%であり、同時両側95%とは呼ばない。threshold、lambda、margin.05を結果後に変更していない。wealth未到達を同等・劣性の証明へ置換しない。停止後の通常固定n CIや、新閾値による救済も行わない。

最大capacity200blockについて全未登録slotを未知とする**記述用**識別区間は[19/240,1097/1200]=[.07916667,.91416667]。これは有限capacity全slotの範囲であり、33prefixの逐次wealthやその条件付き平均の推論対象とは別である。未来1002gameをwealthへゼロ追加しない。旧epoch1の6登録gameは資格品質[0,1]、NI633/1200・劣性531/960の別wealthとして保存されており、epoch2へ移していない。

## 結果前版と停止規則

preregister-e2.json現物はGit8e14cf496047f3c2f19a5824abd219c82ce3b54fの内容と一致。theta.45、閾値20、両lambda集合、core[2,4,6]、200block容量、時計、empty-category全proposal拒否、固定target/4096proposal上限というepoch2抽出、provider/同ONNXをその結果前版から参照した。freezeの18source SHAは現物一致。ready_UTC07:23:35.889552はrun開始07:24:12.222015より前。これは保存版の対応を支持し、全期間のsource不変や抽出代表性を完全保証するものではない。

33blockのadmissionは各launch前、順序飛越しなし。保存resultはprimary=null、SCIENCE_DEADLINE_HEADROOM。事前pool規則は科学終了07:55:00までの残秒又は総heavy残秒が305未満なら次blockを開始しない。終了07:50:17.742340時点で科学期限まで282.257660秒であり、このheadroom停止と整合する。閾値による成功停止を後付けした結果ではない。34以降を補充・実施済み扱いにしない。

新epochのentropy/対象・品質資格と旧epochの管理失敗は分離されている。fresh seedや均等core割付だけでは、stationaryな共通条件付き平均を証明しない。機械競合、core差、時間drift、条件付き開始分布の代表性は未証明。数学的な逐次検定の妥当性と、実環境でのモデル仮定成立を区別する。

## 保存clock、counter、停止の有限支持

core journalsをstream読取し、8268公開手を198game ID/登録slot/終局手数へ対応。最終手playerとGOAL winner、最終keyのgoal座標も独立照合した。各公開CPのgeneration、controller receive≤admit≤402ms、public≤500ms、NN started=returned、zero activeNN0/handles0/activefalse、次t0≥前quiescent gateと保存gapの算術一致を確認。逸脱0。epoch2でNN started/returnedは537460、startup6は別分母。close receiptsのcore別NN総計も537460と一致した。

| 保存最大値 | ms | 注記 |
| --- | ---: | --- |
| 採用CP actual admit/end | 401.998649985 | core6/game119/gen1540、402との差約.001350ms |
| public | 420.955447018 | 500以内 |
| cutoff timer callback | 411.998980999 | callback遅れと採用endを区別 |
| firstCP | 120.740303010 | core2/game14 |
| 原因側post-public cleanup | 14.666054994 | core2/game163 |

402近傍の記録はcontroller単一monotonicの有限支持であり、表示差を実CPUcycle余裕や時計精度保証へ換算しない。cutoff callbackが402を越えても、採用のactualend402とは別であり違反lossを捏造しない。保存arena sourceは次探索前に両engine pendingを確認し、結果後のzero/自pendingを判定する。独立検算は保存journalとsource対応に依存し、API await/IPC待ちをkernel CPUへ換算していない。

stopのremaining/unknown_ownedは空、inner close各exit0、monitor READY/failure null、outer waitの保存SHAを参照。科学停止とmetadata helper/packの継続を区別し、whole_writer_stopped=falseを全writer停止へ補完しない。必要raw/metadataの読取SHAを保存し、再読時同SHAでsnapshotの安定を確認した。pack正本へ将来移動した場合はこのmember/hashでstream復元できる。原rawコピー・全archive展開0。

全198棋譜のRuleA深部独立再生を今回追加していない。owner自己replay支持と共有RuleA/sourceに依存する部分を区別する。今回の終局score/slot/時計算術対応を、全探索・合法性・全host/全期間・kernelCPU同値・途中drift保証へ広げない。保存欠測をpassへ埋めていない。

## 総費と最大1次案

epoch2 job wallは1565.520325秒、198/1565.520325≈.1265game/s（約7.59game/min）。3arenaでの実wholegame総費が得られたが、他の版・並列数への倍率保証ではない。33block elapsedの合計1473.453023秒はjob wallと別分母で、差を単一原因に帰属させない。

各core public数2784/2750/2734。NN537460、discard7271、terminal-noNN1484984、CP received2015173/admitted2008555/late discard6618/schema reject0。API duration合計2372.418195秒、pipe duration合計2819.002431秒、公開clock合計3396.599316秒は並列・包含区間を持つ。これらを加算して総job費とせず、異なる対局経路のC/R NN比から速度差を因果認定しない。

**次案は、別系統の小さいnative教師生成を既学習入口へ接続し、終局後1手1行のπ/rootmean/z/side/lineageを出すこと。** 今回の198gameは正式holdoutとして保持し、学習・教師選定へ転用しない。新生成のゲームlineage単位でtrain/validationを分離し、教師側出所とvalue視点を既契約で照合する。約201万CPの逐次出力に比べ、採用手/教師行8268という記述粒度の差は、最終root visit方策を1回だけ保存する小export契約を選ぶ根拠になる。実際の輸送/保存削減効果は未測であり、policy・推論・探索量の勝手な変更や、今回のholdout転用ではない。

NI未支持を理由に同NI反復・全時計保証・NNUE主実装へ自動連鎖しない。学習接続では有効教師行/総job秒を測り、teacher fittingを棋力認定と分け、後続arenaを独立にする。新実行は今回0。

## 判定と引渡し

支持: 登録済198品質分母、全prefix exact未到達、事前headroom停止から「不確か」とする結論。保存clock/counter/closeの有限対応。

不支持: NI達成、実用上劣性達成、600pair完成、browser NI/最高棋力への読み替え。

不足: stationary conditional mean、抽出の実戦代表性・感度、kernelCPU exact/途中drift/深部独立RuleA保証。今回のscope外事項を新しい入口gateにしない。

独立checkはCPU0単1、.304676秒、RSS peak88,428,544B<896MiBguard。PID終了確認、科学source/子停止をsnapshot-stop.jsonに保存。管理/読取は保守20秒、科学を含むstatic120秒内。保存会計は旧未知88,190,086Bを減額せず、既data/tools実量と新metadata/in-memoryGit forecast2MiBを加え94,424,198B<critic112MiBguard。親追加予約0/fullprivateindex0。必要Git復元/Beadsbackup/配送は175 handoffを参照。本人issueは統括受入れ・close待ち、goal/他者close0。
