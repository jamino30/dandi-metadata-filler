from doi_extraction import DOIExtraction

import sys

def main():
    dandiset_id = "000409/draft"
    doi = "10.1101/2020.01.17.909838"

    # dandiset_id = str(input("Enter a dandiset ID >> "))
    # doi = str(input("Enter a related DOI >> "))

    if "arxiv" in doi.lower():
        print("arXiv assigned DOI's are not supported.")

    doi_extraction = DOIExtraction(doi=doi, dandiset_id=dandiset_id)
    st = "The International Brain lab (IBL) aims to understand the neural basis of decision-making in the mouse by gathering a whole-brain activity map composed of electrophysiological recordings pooled from multiple laboratories. We have systematically recorded from nearly all major brain areas with Neuropixels probes, using a grid system for unbiased sampling and replicating each recording site in at least two laboratories. These data have been used to construct a brain-wide map of activity at single-spike cellular resolution during a decision-making task. In addition to the map, this data set contains other information gathered during the task: sensory stimuli presented to the mouse; mouse decisions and response times; and mouse pose information from video recordings and DeepLabCut analysis."
    print(doi_extraction.create_dandiset_structure())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
