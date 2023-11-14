from crossref.restful import Works

from dandi.dandiapi import DandiAPIClient
from dandischema.models import (
    Person,
    Organization,
    Contributor,
    Affiliation,
    RoleType
)

import requests
import re
import concurrent.futures


class DOIExtraction:
    def __init__(self, doi: str):
        self.doi = doi.strip()
        self.works = self.validate_doi(self.doi)
        if not self.works:
            raise ValueError("Invalid DOI provided.")

        self.contributors = self.works.get("author", [])

        self.dandi_client = DandiAPIClient()

    def validate_doi(self, doi: str):
        """Validate a DOI source is crossref."""
        try:
            works = Works().doi(doi=doi)
            return works
        except Exception:
            return None
    
    def get_contributors(self) -> list[Contributor]:
        """
        Extract contributors for a specific DOI:
        - Authors
        - Organizations
        """
        dandiset_contributors = []

        with concurrent.futures.ThreadPoolExecutor() as exec:
            futures = []
            for contributor in self.contributors:
                futures.append(exec.submit(self.process_contributor, contributor))

            for future in concurrent.futures.as_completed(futures):
                dandiset_contributors.append(future.result())

        return dandiset_contributors

    def process_contributor(self, contributor):
        affiliation = contributor.get("affiliation", None)
        if affiliation == []:
            affiliation = None

        if any(key in contributor for key in ["ORCID", "family", "given"]):
            family_name = contributor.get("family", None)
            given_name = contributor.get("given", None)
            if not family_name or not given_name:
                name = None
            else:
                name = f"{family_name.strip().title()}, {given_name.strip().title()}"

            orcid = contributor.get("ORCID", None)
            if orcid:
                orcid = orcid.split("/")[-1]
                email, url = self.get_info_from_orcid(orcid)
            else:
                email, url = None, None
            # person
            schema: list[Person] = self.filled_person_schema(
                orcid=orcid,
                name=name,
                email=email,
                url=url,
                role=contributor.get("role", None),
                affiliation=contributor.get("affiliation", None),
            )
        else:
            # organization
            schema: list[Organization] = self.filled_organization_schema(
                ror=contributor.get("ROR", None),
                name=contributor.get("name", None),
                email=contributor.get("email", None),
                url=contributor.get("url", None),
                role=contributor.get("role", None),
                affiliation=contributor.get("affiliation", None),
            )

        return schema


    def filled_person_schema(
            self,
            orcid,
            name,
            email,
            url,
            role,
            affiliation,
    ):
        """Return dandischema.models.Person contributor"""
        affiliations = []
        for aff in affiliation:
            affiliations.append(
                Affiliation(
                    schemaKey="Affiliation",
                    identifier=aff.get("id", None),
                    name=aff.get("name", None)
                )
            )
        person = Person(
            schemaKey="Person",
            identifier=orcid,
            name=name,
            email=email,
            url=url,
            roleName=[RoleType.Author], # default given to any author recognized in provided DOI
            affiliation=None if not affiliation else affiliation,
            includeInCitation=True
        )
        return person
                

    def filled_organization_schema(
            self,
            ror,
            name,
            email,
            url,
            role,
            affiliation # not used for dandischema.models.Organization
    ):
        """Return dandischema.models.Organization contributor"""
        organization = Organization(
            schemaKey="Organization",
            identifier=ror,
            name=name,
            url=url,
            email=email,
            roleName=role,
            includeInCitation=True
        )
        return organization
            

    def stringify_contributors(self):
        contributors = self.get_contributors()

        text = "CONTRIBUTORS:\nAuthors:\n{}\nOrganizations:\n{}"

        persons_text = ""
        organizations_text = ""
        for contributor in contributors:
            if not contributor.name:
                    continue
            
            if isinstance(contributor, Person):
                if contributor.identifier:
                    persons_text += f"- {contributor.name}\n\t- ORCID: https://orcid.org/{contributor.identifier}\n\t- EMAIL: {contributor.email}\n\t- URL: {contributor.url}\n\t- AFFILIATIONS: {contributor.affiliation}\n\n"
                else:
                    persons_text += f"- {contributor.name}\n\n"

            elif isinstance(contributor, Organization):
                organizations_text += f"- {contributor.name}\n\n"
            else:
                continue

        if not persons_text:
            persons_text = "None\n"
        if not organizations_text:
            organizations_text = "None\n"

        return text.format(persons_text, organizations_text)


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
            if email:
                final_email: str = email
            else:
                final_email = None

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

    def get_keywords_from_abstract(self):
        keywords = set()
        for subject in self.get_subjects():
            keywords.add(subject.strip().lower())
        return keywords
    

    def stringify_keywords(self):
        keywords = self.get_keywords_from_abstract()

        text = "KEYWORDS:\n"

        for kw in keywords:
            text += f"- {kw}\n"

        return text
    

    def get_references(self):
        """Related resources (relation: dcite:isDescribedBy)"""
        references = self.works["reference"]
        return references
    

    def stringify_references(self):
        pass


    def stringify(self):
        contributors = self.stringify_contributors()
        keywords = self.stringify_keywords()

        return f"{contributors}\n{keywords}"


    def get_title(self) -> str:
        return self.works.get("title", None)
    

    def get_abstract(self) -> str:
        return self.works.get("abstract", None)
    

    def get_subjects(self) -> list[str]:
        return self.works.get("subject", [])


