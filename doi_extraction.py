from crossref.restful import Works

from dandi.dandiapi import DandiAPIClient
from dandischema.models import (
    Person,
    Organization,
    Affiliation
)

class DOIExtraction:
    def __init__(self, doi: str):
        self.doi = doi.strip()
        self.works = self.validate_doi(self.doi)
        if not self.works:
            raise ValueError("Invalid DOI provided.")

        self.contributors = self.works.get("author", [])

    def validate_doi(self, doi: str):
        try:
            works = Works().doi(doi=doi)
            return works
        except Exception:
            return None
    
    def get_contributors(self):
        dandiset_contributors = []

        for contributor in self.contributors:
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

                # person
                schema = self.filled_person_schema(
                    orcid=orcid,
                    name=name,
                    email=contributor.get("email", None), # NOTE: get from ORCID
                    url=contributor.get("url", None),
                    role=contributor.get("role", None),
                    affiliation=contributor.get("affiliation", None),
                )
            else:
                # organization
                schema = self.filled_organization_schema(
                    ror=contributor.get("ROR", None),
                    name=contributor.get("name", None),
                    email=contributor.get("email", None),
                    url=contributor.get("url", None),
                    role=contributor.get("role", None),
                    affiliation=contributor.get("affiliation", None),
                )
            dandiset_contributors.append(schema)

        return dandiset_contributors


    def filled_person_schema(
            self,
            orcid,
            name,
            email,
            url,
            role,
            affiliation,
    ):
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
            url=url,
            email=email,
            roleName=role,
            affiliation=affiliations,
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
            affiliation # not used for dandischema.Organization
    ):
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
                    persons_text += f"- {contributor.name} (https://orcid.org/{contributor.identifier})\n"
                else:
                    persons_text += f"- {contributor.name}\n"

            elif isinstance(contributor, Organization):
                organizations_text += f"- {contributor.name}\n"
            else:
                continue

        if not persons_text:
            persons_text = "None\n"
        if not organizations_text:
            organizations_text = "None\n"

        return text.format(persons_text, organizations_text)


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
    
    
    def get_references(self):
        return self.works["reference"]


