import argparse
import os

from src.pipeline import Config, run
from src.io_out import save_fig, save_csv


def main():
    ap = argparse.ArgumentParser(description="NC SSS 검증 파이프라인")
    ap.add_argument("path_a")
    ap.add_argument("path_b")
    ap.add_argument("--var-a", default=None)
    ap.add_argument("--var-b", default=None)
    ap.add_argument("--ref", default="auto", choices=["auto", "a", "b"])
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    cfg = Config(ref=args.ref, var_a=args.var_a, var_b=args.var_b,
                 outdir=args.outdir)
    res = run(args.path_a, args.path_b, cfg)

    save_csv([res["stats"]],
             os.path.join(args.outdir, "tables", "stats.csv"))
    save_fig(res["figure"],
             os.path.join(args.outdir, "figures", "step5_scatter.png"))
    s = res["stats"]
    print(f"[ref={res['ref_name']} vs eval={res['eval_name']}] "
          f"N={s['N']} Bias={s['Bias']:.3f} RMSE={s['RMSE']:.3f} R={s['R']:.3f}")


if __name__ == "__main__":
    main()
