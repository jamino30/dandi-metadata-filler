from crossref.restful import Works

import requests
import re


class CrossRef:
    def __init__(self):
        self.works = Works()
        self.metadata = None


    def get_doi_metadata(self, doi: str) -> dict:
        try:
            self.metadata = self.works.doi(doi=doi)
            return self.metadata
        except Exception:
            return None


    def get_info_from_orcid(self, orcid: str):
        if not orcid:
            return None, None
        
        orcid_api_url = f"https://pub.orcid.org/v3.0/{orcid}/person"
        headers = {"Accept": "application/json"}

        response = requests.get(orcid_api_url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            emails = data.get("emails", None)
            email = emails.get("email", None) if emails else None
            email = email[0].get("email", None) if email and len(email) > 0 else None
            final_email = email if email else None

            urls = data.get("researcher-urls", None)
            url = urls.get("researcher-url", None) if urls else None
            url = url[0].get("url", None) if url and len(url) > 0 else None
            if url and "value" in url:
                final_url: str = url["value"]
                if final_url.startswith("https://"):
                    final_url = re.sub(r"https://", "http://", final_url)
                elif not final_url.startswith("http://"):
                    final_url = "http://" + final_url.strip()
            else:
                final_url = None

            return final_email, final_url
        
        return None, None
    

    def get_contributors(self):
        if self.metadata:
            contributors = self.metadata.get("author", None)
            return contributors
    

    def get_author_affiliations(self, contributor: dict):
        affiliations = contributor.get("affiliation", None)
        return affiliations
    
    
    def get_author_full_name(self, contributor: dict) -> (str, str):
        family_name = contributor.get("family", None)
        given_name = contributor.get("given", None)        
        return family_name, given_name
    

    def get_author_orcid(self, contributor: dict) -> str:
        orcid = contributor.get("ORCID", None)
        return orcid
    

    def get_subjects(self) -> list[str]:
        if self.metadata:
            subjects = self.metadata.get("subject", None)
            return subjects
        

    def get_title(self) -> str:
        if self.metadata:
            title = self.metadata.get("title", None)
            return title
        
    
    def get_abstract(self) -> str:
        if self.metadata:
            abstract = self.metadata.get("abstract", None)
            return abstract