\
import argparse, os, glob, pandas as pd
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="results")
    ap.add_argument("--out", type=str, default="results/plots")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    files = glob.glob(os.path.join(args.input, "*.csv"))
    if not files:
        print("No CSVs found in", args.input)
        return

    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    g = df.groupby(["strategy","provider"])["crisis_score"].agg(["mean","std"]).reset_index()
    labels = g.apply(lambda r: f"{r['strategy']}\\n{r['provider']}", axis=1)
    plt.figure()
    plt.bar(labels, g["mean"])
    plt.title("CrisisScore by strategy/provider (mean)")
    plt.ylabel("CrisisScore")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "crisis_score_comparison.png"))
    plt.close()

    plt.figure()
    df.boxplot(column="invalid_json", by="provider")
    plt.suptitle("")
    plt.title("Invalid JSON counts by provider")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "json_error_boxplot.png"))
    plt.close()

    print("Plots saved to", args.out)

if __name__ == "__main__":
    main()
