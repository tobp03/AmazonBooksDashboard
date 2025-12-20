from pathlib import Path
import subprocess
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
DATASET_DIR = ROOT_DIR / "dataset"
REQUIRED_OUTPUTS = [
    DATASET_DIR / "processed_metadata.csv",
    DATASET_DIR / "scorecard_data.csv",
    DATASET_DIR / "genre_data.csv",
    DATASET_DIR / "books_reviews_clean.csv",
]


def outputs_ready() -> bool:
    return all(path.exists() for path in REQUIRED_OUTPUTS)


def run_preprocessing() -> None:
    subprocess.run([sys.executable, "dataprocessing.py"], check=True)


st.set_page_config(page_title="Amazon Books Dashboard", layout="wide")
st.title("Amazon Books Dashboard")

st.markdown(
    """
This is the landing page. Use the sidebar to open:
- `dash1` (Main Dashboard)
- `dash2` (Author Insights)
"""
)

if not DATASET_DIR.exists():
    st.error("Dataset folder is missing. Run preprocessing locally and commit outputs.")
    st.stop()

if not outputs_ready():
    st.warning("Required dataset outputs are missing.")
    if st.button("Run preprocessing"):
        with st.spinner("Running dataprocessing.py..."):
            run_preprocessing()
        st.success("Preprocessing complete. Refresh the page.")

files = sorted(p.name for p in DATASET_DIR.iterdir())
if files:
    st.subheader("Available files in dataset/")
    st.code("\n".join(files))
else:
    st.warning("Dataset folder is empty. Run preprocessing locally and commit outputs.")


if __name__ == "__main__":
    if not outputs_ready():
        print("Running data processing...")
        run_preprocessing()
        print("Data processing completed successfully!")
    print("Preprocessing complete. Run `streamlit run main.py` to launch the app.")
