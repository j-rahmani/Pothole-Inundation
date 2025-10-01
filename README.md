# Inundation

Reproducible Code for "Wetlands Set the Pace of Annual Runoff in the Northern Great Plains"  
This research article is currently submitted to a scientific journal and is under review.


## Project structure
Pothole-Inundation/
│── README.md
│── requirements.txt	 # Required python libraries to run the code
│── environment.yml      # (optional, for conda users)
│── LICENSE
│── Analysis.py          # Main analysis script
│── Data/                # Input files (not tracked in repo)
│── Outputs/             # Generated figures
│── Expected_Outputs/    # Expected figures



### Installation Using Conda
	conda env create -f environment.yml
	conda activate Inundation
	
### Installation Using pip
	pip install -r requirements.txt
	
#### Usage
	Run the analysis:
		python Analysis.py
	Results (figures and processed datasets) will appear in the Pothole-Inundation/Outputs/ folder.
	Compare the generated figures (Pothole-Inundation/Outputs/) with the expected ones (Pothole-Inundation/Expected_Outputs/).
	
	
##### License
This project is licensed under the MIT License — see the LICENSE file for details.
