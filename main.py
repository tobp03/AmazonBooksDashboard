import os
import subprocess
import sys

OUTDIR = "./dataset"
REQUIRED_OUTPUTS = [
    f"{OUTDIR}/processed_metadata.csv",
    f"{OUTDIR}/scorecard_data.csv",
    f"{OUTDIR}/genre_data.csv",
    f"{OUTDIR}/books_reviews_clean.csv",
]


def outputs_ready() -> bool:
    return all(os.path.exists(path) for path in REQUIRED_OUTPUTS)

def main():
    if not outputs_ready():
        print("Running data processing...")
        result = subprocess.run([sys.executable, "dataprocessing.py"], check=True)

        if result.returncode == 0:
            print("Data processing completed successfully!")
        else:
            print("Data processing failed!")
            sys.exit(1)
    else:
        print("Dataset already processed; skipping download/processing.")

    print("\nLaunching Streamlit dashboard...")
    subprocess.run(["streamlit", "run", "dash1.py"])


if __name__ == "__main__":
    main()
