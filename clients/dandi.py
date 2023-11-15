from dandi.dandiapi import DandiAPIClient
from dandischema.models import (
    Dandiset,
    Person,
    Organization,
    Affiliation,
    RoleType
)


class DandiClient:
    def __init__(self):
        self.client = DandiAPIClient()
        self.metadata = None


    def get_dandisets(self):
        return self.client.get_dandisets()
    

    def get_dandiset(self, dandiset_id: str, dandiset_version: str = "draft") -> Dandiset:
        try:
            dandiset = self.client.get_dandiset(dandiset_id, dandiset_version)
            return dandiset
        except Exception:
            return None
        

    def get_raw_metadata(self, dandiset_id: str, dandiset_version: str = "draft") -> dict:
        dandiset = self.client.get_dandiset(dandiset_id, dandiset_version)
        if not dandiset:
            return None
        self.metadata = dandiset.get_raw_metadata()
        return self.metadata
    

    def get_dandiset_name(self):
        if self.metadata:
            name = self.metadata.get("name", None)
            return name
    

    def get_dandiset_description(self):
        if self.metadata:
            description = self.metadata.get("description", None)
            return description


    def filled_person_schema(
        self,
        orcid,
        name,
        email,
        url,
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
    ):
        """Return dandischema.models.Organization contributor"""
        organization = Organization(
            schemaKey="Organization",
            identifier=ror,
            name=name,
            url=url,
            email=email,
            includeInCitation=True
        )
        return organization