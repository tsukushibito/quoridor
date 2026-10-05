from pathlib import Path
import json,datetime
O=Path('research-data/ai-sigma/frame16-teacher-throughput/codec-control');r=json.loads((O/'comparison.json').read_text());m=r['mean_comparison'];names=['codec-r1','codec-confirmation'];w=m['codec_meanwall'];density=sum(r['conditions'][n]['qualified_joint']for n in names)/96
qualification=sum(json.loads((O/(n+'-summary.json')).read_text())['qualify_wall_s']for n in names)/96
pack=json.loads((O/'archive-manifest.json').read_text());archiveB=pack['archive_B'];pack_per_game=pack['wall_s']/96
rawB=sum(p.stat().st_size for p in(O/'jobs').rglob('*')if p.is_file())/96
saved=m['savedseconds_per_game'];knownC=r['allattempt']['wall_s']-sum(r['conditions'][n]['jobwall_s']for n in names)+qualification*96+pack['wall_s']
scenarios=[]
for g in[100,1000,10000]:
 job=g*w/48;pipe=job+g*(qualification+pack_per_game);scenarios.append(dict(games_scenario_only=g,job_minutes=job/60,known_generation_qualification_pack_minutes=pipe/60,unknown_additional='dispatch/backup/sourcefreeze/dev/production-tail/distribution/larger-save costs',joint_rows=density*g,archive_B_estimate=archiveB/96*g,retained_raw_B_estimate=rawB*g,actual_scale_executed=False))
x=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),density_joint_per_game=density,codec_meanwall_s=w,graph_meanwall_s=m['graph_B8_baseline_meanwall'],job_joint_rate=density*48/w,known_qualification_s_per_game=qualification,known_pack_s_per_game=pack_per_game,scenarios=scenarios,targets=dict(initial_60minutes='short matchedwork extrapolation inside60 with unknown costs retained',next_30minutes='assess known pipeline estimate; no actual1000completed',required_joint_per_s_60=density*1000/3600,required_joint_per_s_30=density*1000/1800),break_even=dict(saved_job_seconds_per_game=saved,known_incremental_parity_admission_qualification_pack_s=knownC,known_component_recovery_games=knownC/saved if saved>0 else None,development_estimate_s=900,development_plus_known_recovery_games=(900+knownC)/saved if saved>0 else None,development_actual_seconds_unknown=True,delta_uncertain='only matched ordered pair; hostwarm/batch/tail/nonconcurrent baseline'),cost_spans_overlap=True,individual_codec_components_cause=False,K64_not_K800_quality_equivalence=True)
(O/'scenarios.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
