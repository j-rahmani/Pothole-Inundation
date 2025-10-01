# Reproducible Code for *"Wetlands Set the Pace of Annual Runoff in the Northern Great Plains"*

This repository contains the analysis code developed for the manuscript currently under review.  
It is designed to allow reviewers and readers to reproduce the figures and results presented in the paper.

---

## 📂 Repository Structure
```
Pothole-Inundation/
│── README.md
│── requirements.txt
│── environment.yml
│── LICENSE
│── src/
│    ├── Analysis.py       # Main analysis script
│    ├── Data/             # Input data (unzipped from `data.zip`)
│    └── Outputs/          # Generated figures and tables
│── Expected_Outputs/      # Reference figures for comparison
```

---

## ⚙️ Installation

### Option 1 — Using Conda (recommended)
```bash
conda env create -f environment.yml
conda activate Inundation
```

### Option 2 — Using pip
```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Analysis
1. **Unzip the dataset**  
   Extract the provided `data.zip` archive into the folder:
   ```
   src/Data/
   ```

2. **Run the analysis**  
   From the `src/` directory, run:
   ```bash
   python Analysis.py
   ```

3. **View results**  
   - All generated figures and processed datasets will appear in:
     ```
     src/Outputs/
     ```
   - Compare the results with the reference figures provided in:
     ```
     Expected_Outputs/
     ```

---

## 📜 License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
