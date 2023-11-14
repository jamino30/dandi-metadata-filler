from doi_extraction import DOIExtraction

import sys

def main():
    dandiset_id = "000409/draft"
    doi = "10.1101/2020.01.17.909838"

    if "arxiv" in doi.lower():
        print("arXiv assigned DOI's are not supported.")

    doi_extraction = DOIExtraction(doi=doi)

    print(doi_extraction.stringify())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)