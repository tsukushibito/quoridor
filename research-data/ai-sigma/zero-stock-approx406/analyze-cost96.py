"""Present the original finite96 saved observations without new Search or sampling."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path("/workspaces/quoridor")
BASE = Path(__file__).resolve().parent
OUT = BASE / "final-results-v1"
loader = importlib.util.spec_from_file_location(
    "lc", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
sys.modules["lc"] = lc
loader.loader.exec_module(lc)


def main():
    OUT.mkdir()
    source = lc.artifact_ref(BASE / "cost96-v1/collection-v1/result.json")
    r = lc.document(source)
    assert (r["calls"], r["COMPLETE"], r["UNKNOWN"], r["nodes"]) == (
        96,
        72,
        24,
        137938286,
    )
    conditions = []
    for condition in r["conditions"]:
        selected = [
            p
            for p in r["passes"]
            if p["evaluator"] == condition["evaluator"]
            and p["threshold"] == condition["threshold"]
        ]
        assert len(selected) == 2
        rows = [row for p in selected for row in p["rows"]]
        baseline = next(
            c
            for c in r["conditions"]
            if c["evaluator"] == condition["evaluator"] and c["threshold"] is None
        )
        conditions.append(
            dict(
                **condition,
                calls=len(rows),
                whole_ratio_to_none=condition["whole_median_seconds"]
                / baseline["whole_median_seconds"],
                nodes=sum(v["measurement"]["work"]["nodes"] for v in rows),
                evaluations=sum(v["measurement"]["work"]["evaluations"] for v in rows),
                delta_updates=sum(
                    v["measurement"]["work"]["delta_updates"] for v in rows
                ),
                approx_terminations=sum(
                    v["measurement"]["work"]["zero_stock_approx_terminations"]
                    for v in rows
                ),
                session_reset_seconds=[
                    sum(
                        d["seconds"]
                        for d in lc.document(
                            lc.artifact_ref(
                                Path(p["manifest"]["path"]).parent.parent
                                / "data/result.json"
                            )
                        )["session_domains"]
                        if d["domain"] == "reset"
                    )
                    for p in selected
                ],
            )
        )
    comparisons = []
    for evaluator in ("nnue", "distance"):
        for threshold in (4, 0):
            for walls in (6, 4, 2, 0):
                for temperature in ("cold", "warm"):

                    def matches(row):
                        return (
                            row["evaluator"] == evaluator
                            and row["root_walls"] == walls
                            and row["temperature"] == temperature
                        )

                    base = next(
                        x
                        for x in r["root_summary"]
                        if matches(x) and x["threshold"] is None
                    )
                    actual = next(
                        x
                        for x in r["root_summary"]
                        if matches(x) and x["threshold"] == threshold
                    )
                    comparisons.append(
                        dict(
                            evaluator=evaluator,
                            threshold=threshold,
                            walls=walls,
                            temperature=temperature,
                            enabled=actual["permitted"],
                            nodes_ratio=actual["work"]["nodes"] / base["work"]["nodes"],
                            Search_time_ratio=actual["Search_median_seconds"]
                            / base["Search_median_seconds"],
                            same_status_depth_value_action_PV=all(
                                actual[k] == base[k]
                                for k in [
                                    "status",
                                    "stop",
                                    "depth",
                                    "value_bits",
                                    "action",
                                    "PV",
                                ]
                            ),
                            same_all_work=actual["work"] == base["work"],
                            value_changed=actual["value_bits"] != base["value_bits"],
                            action_changed=actual["action"] != base["action"],
                            PV_changed=actual["PV"] != base["PV"],
                        )
                    )
    assert all(
        x["same_all_work"] and x["same_status_depth_value_action_PV"]
        for x in comparisons
        if x["threshold"] == 4 and x["walls"] in (2, 0)
    )
    fixture_ref = lc.artifact_ref(BASE / "saved-intake-v1/fixture-comparison.json")
    fixture = lc.document(fixture_ref)
    failed_job = lc.document(
        lc.artifact_ref(BASE / "compatible-build-v2/job/result.json")
    )
    passed_job = lc.document(
        lc.artifact_ref(BASE / "compatible-build-v3/job/result.json")
    )
    result = dict(
        scope="Original same-image finite96 speed-first observations only; no games/default promotion/new parameter selection",
        source=source,
        calls=96,
        sessions=48,
        node_cap=384000000,
        nodes=r["nodes"],
        COMPLETE=72,
        UNKNOWN=24,
        conditions=conditions,
        roots=r["root_summary"],
        comparisons=comparisons,
        approx_formula="wall-distance side-to-move race ds<=do +1 else-1 nonterminal; not exact gameWDL",
        fixture=fixture_ref,
        fixture_confusion=fixture["confusion"],
        fixture_active=fixture["active"],
        Draw_fixture_labels=fixture["draw_labels_observed"],
        all_replicates_status_depth_value_action_PV_allwork_exact=True,
        threshold4_disabled_roots2and0_same_baseline_values_PV_allwork=True,
        actual_TT_entries=1048576,
        TT_retained_bytes=83886128,
        RSS_peak="UNKNOWN; family4GiB actual guard completed without resource refusal",
        cost=dict(
            original_speed_outer_seconds=r["outer_seconds"],
            whole_pass_seconds_sum=sum(p["whole_seconds"] for p in r["passes"]),
            original_software_outer_seconds=failed_job["wall_seconds"]
            + passed_job["wall_seconds"],
            original_failed_software_outer_seconds=failed_job["wall_seconds"],
            nested_scope_not_added=True,
            all_source_LLM_admin_cost="UNKNOWN",
        ),
        decision="Keep research option default null/OFF. No uniform speedup or strength/default adoption; human chooses next numeric scope.407 separate source/software allowed after actual406STOP;407 numeric scope not issued.",
        new_Search_calls_by_analysis=0,
    )
    lc.new_json(OUT / "result.json", result)
    lines = [
        "# 零在庫近似の速度優先有限結果（406）",
        "",
        "同一真正image `43971e3b…` / BUILD `272406e0…`、source Git `7aa63d74…` で、NNUE BEST43と固定D(0,8tanh)を別stratumとして比較した。双方Control・LMR OFF・PVS ON・TT1,048,576、深さ8・各4M nodes、時間上限なし、diagnostics/depthcallback OFF。実入力は指定された元対局4prefix（残壁6/4/2/0）の完全履歴再生である。null→4→0→0→4→null、各4root cold/warmの96 calls・48sessionsを一度だけ実行し、追加sampling・補充・Search再演は0。",
        "",
        "**72 COMPLETE＋24 UNKNOWN、実137,938,286 nodes（上限384M）**。UNKNOWNは残壁6枚rootの全24callで、4M/NodeLimit/completed6/target8。未完成を完成D8へ読み替えない。同条件二反復はrequest/root/status/depth/valuebits/action/PV/全保存work一致。全96のactual settings、合法返却、PV・親と完全history復元、元journal/result対応、全12operationの原PASS/cleanupとfresh process absenceを確認した。これは全callが要求深さを完成したという意味ではない。",
        "",
        "## setup/drop込みwholeと探索仕事",
        "",
        "wholeは8 callsに加えてsetup、session reset/teardown、journal等を含む各pass全体の二反復中央値。時間比は同仕事speedupではなく、評価木・仕事・固定費込みの有限観測である。",
        "",
        "|評価|設定|whole秒（2pass中央値）|なし比|nodes（16calls）|通常評価|差分更新|近似終了|COMPLETE/UNKNOWN|",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def label(value):
        return (
            "なし"
            if value is None
            else ("開始時固定≥4" if value == 4 else "全root許可0")
        )

    for x in conditions:
        lines.append(
            f"|{x['evaluator']}|{label(x['threshold'])}|{x['whole_median_seconds']:.6f}|{x['whole_ratio_to_none']:.6f}|{x['nodes']:,}|{x['evaluations']:,}|{x['delta_updates']:,}|{x['approx_terminations']:,}|{x['COMPLETE']}/{x['UNKNOWN']}|"
        )
    lines += [
        "",
        "NNUEのwholeは約0.9%短い一方、固定Dでは約11%長い。n=2・固定順序・この4rootの結果で、一律高速化や最適閾値は支持しない。TT retained bytes/generationはgaugeなので合計workへ加算しない。上表の通常評価・差分更新・近似終了は保存scalarの別分母であり、物理NNUE forward件数や部位別時間ではない。",
        "",
        "## 局面別cold/warm",
        "",
        "下表の時間はSearch呼出全体の二反復中央値(ms)。通常評価・差分更新・近似終了、body/journal込み時計、二反復の実値、status/stop/value/PVはresult.jsonへ保存した。coldの実効mode切替に伴うTT/history clear等も呼出全体へ含まれる。",
        "",
        "|評価|設定|残壁|depth cold/warm|Search ms cold/warm|nodes cold/warm|近似終了 cold/warm|",
        "|---|---|---:|---|---:|---:|---:|",
    ]
    for evaluator in ("nnue", "distance"):
        for threshold in (None, 4, 0):
            for walls in (6, 4, 2, 0):
                rr = [
                    next(
                        x
                        for x in r["root_summary"]
                        if x["evaluator"] == evaluator
                        and x["threshold"] == threshold
                        and x["root_walls"] == walls
                        and x["temperature"] == temperature
                    )
                    for temperature in ("cold", "warm")
                ]
                a, b = rr
                lines.append(
                    f"|{evaluator}|{label(threshold)}|{walls}|{a['depth']}/{b['depth']}|{a['Search_median_seconds'] * 1000:.3f}/{b['Search_median_seconds'] * 1000:.3f}|{a['work']['nodes']:,}/{b['work']['nodes']:,}|{a['work']['zero_stock_approx_terminations']:,}/{b['work']['zero_stock_approx_terminations']:,}|"
                )
    lines += [
        "",
        "閾値4は残壁2/0のrootで実効OFFとなり、なしとstatus/depth/value/action/PV/全workが一致した。rootの許可固定が意図どおり近い終盤を通常探索に残すことを確認した。残壁6/4では0と4が同じ有効方式となり、閾値数値そのものを別方式にしない。近似終了件数は全反復と未完了の最終反復を含む累積で、完成深さ6だけの費用へ戻さない。",
        "",
        "全root許可0の残壁2/0ではnodesや通常評価は減るが、時間は一様には減らない。例えばNNUE残壁0のcoldは約0.551ms→4.975ms、warmは0.467ms→0.039ms。初回切替・初期化とwarm再利用を含む境界の違いがあり、nodes減だけでwhole利益を認定しない。固定D残壁4は約1.69M→1.54M cold nodesへ減っても、約0.829s→1.159s。距離fallback、切替、探索仕事と呼出費を含み、孤立したTT clear/BFS/近似式等の時計は未記録なので原因別費はUNKNOWN。",
        "",
        "全root許可0の残壁2/0では、今回のroot actionは同じでもvaluebitsとPVが変わる。正常終局の2を非終局近似の1へ置換して読ませる例もあり、近似入りcompleted8はその評価方針の名目深さであって、通常全幅depth8やゲームのexact WDLではない。真のgoal/threefold優先を消したという意味でもない。",
        "",
        "## 保存52fixtureの誤判定",
        "",
        f"保存ラベルのみを照合した5,680 active小盤面状態で、Win→Loss {fixture['confusion']['W_to_L']}、Loss→Win {fixture['confusion']['L_to_W']}。Win→Win {fixture['confusion']['W_to_W']}、Loss→Loss {fixture['confusion']['L_to_L']}。元52fixtureにはDrawラベル0で、その誤判定は未観測。式自体は±1だけでDrawを表現しない。元WDL solver/合法辺/rankの再実行は0。小盤面board-onlyの照合を9×9・実履歴・訪問分布・棋力へ一般化しない。",
        "",
        "## 費用・停止・判断",
        "",
        f"元speed sequence outerは{r['outer_seconds']:.9f}s、12pass whole合計は{sum(p['whole_seconds'] for p in r['passes']):.9f}sでnested値をouterへ足さない。元software二jobの非重複outer合計は{failed_job['wall_seconds'] + passed_job['wall_seconds']:.9f}s（FAILED {failed_job['wall_seconds']:.9f}sを含む）。source/LLM/admin/保存解析を含む全費用、物理NNUE forward、部位別時計、continuous RSS peakはUNKNOWN。実TT本体は各session83,886,128BでRSSではない。family4GiB/GPU0の実guard内で完了した。",
        "",
        "原BUILD v2のE0063/FAILED、既存fixtureへNoneを加えた別修復、guardian returned NULLとpersisted pending/attempted等の違い、初回collectorのmanifest生成前の読取仮定、SHA入力のpreflight拒否、Rootのclose owner fence拒否を保持する。最初の失敗を成功へ書き換えず、真正image作成後の科学実行は今回の元96だけ。元journal/RAW・入力・モデルを保全し、旧trialへ数値を遡及しない。",
        "",
        "実native/sequence readerSTOPは2026-10-15T03:39:18.372901Z。49個の元native/guard/outer identityをfresh absent/different、directwait/reap、handles/TMP/lease解放として確認し、407の通常作業へ境界を通知した。保存collectorも別STOP/owned[]を保持する。",
        "",
        "**研究optionを既定null/OFFのまま保持し、今回の有限結果から一律高速化・棋力・製品/生成既定採用は決めない。** 人間が速度結果を見て次を判断するまで対局・追加閾値比較・新学習は発行しない。407の方法選択は別差分のsource/softwareであり、この406の式・image・入力・結果を変更しない。mixed/learner全prep/pipelineと323 USERPAUSE、defaults/models/weights/seals/oldfits96/foreign変更、旧RAW/FAILED/費UNKNOWNを維持する。",
    ]
    (OUT / "report-ja.md").write_text("\n".join(lines) + "\n")
    assert lc.artifact_ref(source["path"]) == source


if __name__ == "__main__":
    main()
