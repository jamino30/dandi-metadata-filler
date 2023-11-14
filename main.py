# goal: get the following doi info https://www.biorxiv.org/content/10.1101/2020.01.17.909838v5 using crossrefapi

from doi_extraction import DOIExtraction

dandiset_id = "000409/draft"
doi = "10.1101/2020.01.17.909838"

if "arxiv" in doi.lower():
    print("arXiv assigned DOI's are not supported.")

doi_extraction = DOIExtraction(doi=doi)

# print(doi_extraction.stringify())
print(doi_extraction.stringify())