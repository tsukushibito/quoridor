# Sigma公開zのcanonical接続 — quoridor-4lc.289

固定source `bartolomeo3000/SigmaQuoridor@751186344fc52ad0c29bc65922e62c6fa915f006` の0041/0042/0043だけを取得し、original入力群をnative QF1/cacheへ変換した。新model/fit/forward/対局は0。一般棋力、終局理由が不明な0のdraw認定、独立game数は未認定。

正本は [immutable handoff](../../research-data/ai-sigma/frame23-sigma-public-z-import/public-z-immutable-handoff-v3.json)、[停止束](../../research-data/ai-sigma/frame23-sigma-public-z-import/canonical-import-r2-finite-stop.json)、[全attempt費](../../research-data/ai-sigma/frame23-sigma-public-z-import/allattempt-cost-ledger-v1.json)。producer自己確認と290/291の入力・model parity・評価、統括のsource採否を分ける。

## 有効入力と教師

| partition      | fixed候補original行 | native資格後 | original入力群 | recorded±1適格 |   理由不明z0 |
| -------------- | ------------------: | -----------: | -------------: | -------------: | -----------: |
| 0041 train     |              79,998 |       79,769 |          5,055 |         76,855 |        2,914 |
| 0042 selection |              19,965 |       19,965 |             20 |         19,846 |          119 |
| 0043 future    |              19,359 |       19,359 |             10 |   producer封印 | producer封印 |

80k/20k/20kのcomplete-group capはlabel前に登録した。全originalと後半LRの8plane uint32 byte対応が成立し、後半は使わない。元LRはV辺の正しい反転とは異なる可能性があり、「naive LRは常に不合法」という旧fixture失敗は訂正済み。元rawと旧失敗は保持した。

全originalのtarget-free scanで、残壁plane−0.1を含む行は0041で460/148,967、0042で660/140,967、0043で414/117,171。原因実装/versionは未確定。他planeはfinite 0..1。登録した候補内では0041の229行・113群がこの理由で拒否され、whole-group除外後に補充しなかった。範囲をclipせず、native幾何・全648plane・両81距離mapの既許容差で資格を確認した。

primaryはdecisive recorded outcomesに条件付けたSTM z。公開z0には終了理由/gameIDがなく、規則drawとcap等を区別できないため共通predicateで除外する。全NPZの原z0数はtrain9,280、selection3,840。0を勝敗へ変換せず、nativeで証明済みdraw0とは区別した。rootmean/visits/game/history/absoluteP2は捏造しない。virtual canonicalSTM side1と実P1/P2不明を明記した。

## 露出・分母の限界

target-free gzip JSONLは全input-qualified行を持ち、z0も入力露出参照に残す。gzip復元byte SHA一致後に自分が生成した非圧縮重複だけを除いた。raw/既結果/他ownerデータの削除は0。

[保存入力の小確認](../../research-data/ai-sigma/frame23-sigma-public-z-import/target-free-input-exposure-r1.json)はlabel0/NN0。actualSTM sparse IDsとdistance f32bitsから署名を検算した。train rawの9,051/79,769行がraw selectionとOR一致。futureの15,770/19,359行がraw selection、9,971行がraw trainと一致する。両数は重複し得るので加算しない。futureはALLraw selection除外だけで最大3,589行となる。actualused train・±1 predicate・finalmask後の分母は290/291の正本で確定する。

selection20群・future10群という限られた入力支持範囲と高い反復を保持する。行数を独立game数/代表局面数とは呼ばない。history欠測の空値を共有historyの証拠として使わない。局面の幾何と記録zの対応を確認した範囲であり、履歴・全game合法性・RuleAによる真の最適値は未認証。次に優先する確認は、予定2fitの実露出mask・独立評価分母・入力群別支持範囲を同時に残すこと。範囲拡張や別splitは新しい結果前配分で判断し、自動追加しない。

## 接続・検証・費

generic `sigma-import` のimport/cache/references/input-only qualification/必要旧scalar入口を一つにした。旧rootmean E27/E28の3453行は既候補・設定・mask freeze後に限定してcanonical family+rowIDでjoinし、[旧287 scalar receipt](../../research-data/ai-sigma/frame23-sigma-public-z-import/old287-scalar-handoff-r1.json)をcriticへ渡した。公開0043は別protocolで引き続きproducer封印。

変更Rust/Python/configの担当範囲を整形し、Ruff format/check/lint・rustfmt/check・owned Clippyを実施した。external fixture2PASSと新generic framing/schema/truncation確認が成立。旧library LTO timeout、naive-LR assertion、Clippy失敗、range拒否、private NumPy headerAPI失敗を保持し、成功へ付け替えなかった。whole library suiteの新全面PASSは主張しない。

native binary SHA `e7c25987d432eacb5af218a222ed3437fd37ec3bd6315de9ed82caab16923681`。新import source SHA `47cf73ea1a4289d6881ad3d0d972fb161e7f8065e0902da8679c28e3b4c188a6`、元失敗版`d4ba1a23…d835e`をexact byte復元して別保存。新入口は92修復後の正scheduler1713022/tick47793131・monitor1713041/tick47793161/current24を本人guardで確認した。LLM人数はbusy認定に使わない。

compile/test全attempt command wall199.515768秒/220秒、source/import NN0記録command wall25.603136秒/1800秒。実read/整形/通信/pack/Beads/LLMの未測費はUNKNOWN。重なるcommand/guardian/background spanを合算しない。成功importはcommand11.554116秒、pipeline11.213715秒、guardian inclusive14.985958秒、background inclusive15.305473秒、sampled peakRSS1,328,246,784B。NN/model/fit/GPU推論0。取得登録17:36:16から成功import18:46:55まで約70分39秒には準備・失敗・自然待機が含まれ、CPU科学wallとは別である。

現在source/raw/cache/projection/必要metadataのunique allocated532,127,744B＋必要Git/temp60,817,408B＝592,945,152B<640MiB。621,575,328B/追加build込み655,129,760Bの旧forecastはraw込みのinclusive総額であり、currentに重ねて加算する旧説明は訂正し原記録を保持した。親現在保管の将来withinや未確認freeは認定しない。旧285352MiB・新289640MiB、UNKNOWN128MiB、原科学費とlive NN移譲会計は不変更。
