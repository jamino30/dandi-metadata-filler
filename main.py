from doi_extraction import DOIExtraction

import sys

def main():
    dandiset_id = "000409/draft"
    doi = "10.1101/2020.01.17.909838"

    dandiset_id = str(input("Enter a dandiset ID >> "))
    doi = str(input("Enter a related DOI >> "))

    if "arxiv" in doi.lower():
        print("arXiv assigned DOI's are not supported.")

    doi_extraction = DOIExtraction(doi=doi, dandiset_id=dandiset_id)

    print(doi_extraction.stringify())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)