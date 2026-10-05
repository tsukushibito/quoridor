# 公開z=0の終了理由可用性補足

Beads289/290/291。固定cpp/selfplay.hppを統括が一次source実読。process_game L520–532はwinner()!=0だけでなくdepth>=max_moves又はlegal.emptyでもfinish_game_and_maybe_reset(g,w)へ進み、L617–618 finalize、L1053–1056はwinner==0をvalues0として保存する。selfplay_cpp.py NPZには終局理由/gameIDが無く、0だけから規則drawとcap打切りを区別できない。根拠: https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/selfplay.hpp#L520

actualNPZでz0数を測り、source/原値を保持。初回の主教師は確認された勝敗±1、理由不明0はtyped EXCLUDED_TERMINATION_REASON_UNAVAILABLEでtrain/selection/eval共通predicate、除外全分母を残す。0を勝ち負けへ変換せず、game終局理由をplies_to_end/orderから推測しない。primaryはdecisive recorded outcomesに条件付けたz予測で、全対局含draw期待結果へ一般化しない。別provenanceでtrue drawが証明できるならそのgroupだけ規則0を認めるが、値域検査だけで認定しない。自前285のexplicit terminal_value Some(0) drawは別source根拠で、公開0との同一化0。入力視点/P2/左右兄弟/source版限界は同様に保持。実dataset/teacher品質の負例ではなく可用性不足、公開学習全体を止めるgateにせず±1有効量で実学習へ進む。旧rootmean protocolは不変更。

## 左右兄弟の壁座標検査

goal quoridor-4lc /公開z STM変換のsource-based懸念（actualNPZ未確認）。固定cpp/engine.hpp L432–457はwall segment: H[y,x]は(y,x)-(y+1,x)、V[y,x]は(y,x)-(y,x+1)、Vpadding列N-1=0。一方selfplay_cpp.py L305は全8planeをnp.flip(axis=3)してLR兄弟をconcat、game.py L949–959も全列flipとしています。V辺の正しいLRはx→N-2-xであり、素直なNxN全列flipはx→N-1-xなので、非対称V壁でpadding/距離map不整合の可能性。現sourceだけで全過去NPZ不成立は認定0、actualshard original/aug halfのbyte対応、非対称壁/P2と全81距離をfixtureで判別してください。
originalと第二half LRコピーが実証できた場合は、変換の初期subsetをfirsthalf原位置に限定し兄弟を同group/重複除外するのが低費用。左右augmentationを使うならnative正しい壁反転から再構成し、原rawを変更せず補正provenance・費を別記する。rawLR Vplaneをそのまま合法wallとして捏造/全map距離を盲信しない。全公開data棄却や新管理gateにせず、有効original量からz学習へ。政策plane未使用でもpawn/壁/距離/remainingの整合必要。一次URL https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/engine.hpp#L426 と selfplay_cpp.py#L305 。旧rootmean評価不変更。
