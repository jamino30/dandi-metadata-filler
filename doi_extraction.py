from crossref.restful import Works

from dandi.dandiapi import DandiAPIClient
from dandischema.models import (
    Person,
    Organization,
    Contributor,
    Affiliation,
    RoleType
)

from keybert import KeyBERT

# from langchain.chat_models import ChatOpenAI
# from langchain.chains import create_extraction_chain

import openai
import requests
import re
import concurrent.futures
import os


NUM_KEYWORDS = 10


class DOIExtraction:
    def __init__(self, doi: str, dandiset_id: str):
        self.doi = doi.strip()
        self.works = self.validate_doi(self.doi)
        if not self.works:
            raise ValueError("Invalid DOI provided.")

        self.contributors = self.works.get("author", None)

        self.dandi_client = DandiAPIClient()
        self.dandiset_id = self.validate_dandiset_id_format(dandiset_id.strip())
        if not self.dandiset_id:
            raise ValueError("Invalid Dandiset ID provided.")
        
        openai.api_key = os.environ.get("OPENAI_API_KEY", None)

        self.study_target = None

    def validate_doi(self, doi: str):
        """Validate a DOI source is crossref."""
        try:
            works = Works().doi(doi=doi)
            return works
        except Exception:
            return None
        
    def validate_dandiset_id_format(self, dandiset_id: str):
        """Validate a dandiset ID format is valid."""
        if len(dandiset_id.split("/")) == 2:
            return dandiset_id
        else:
            return None
    
    def get_contributors(self) -> list[Contributor]:
        """
        Extract contributors for a specific DOI:
        - Authors
        - Organizations
        """
        if not self.contributors:
            return None
        
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
                    persons_text += f"- {contributor.name} (ORCID: https://orcid.org/{contributor.identifier}) (EMAIL: {contributor.email}) (URL: {contributor.url}) (AFFILIATIONS: {contributor.affiliation})\n"
                else:
                    persons_text += f"- {contributor.name}\n"

            elif isinstance(contributor, Organization):
                if contributor.identifier:
                    organizations_text += f"- {contributor.name} (ROR: https://ror.org/{contributor.identifier}) (EMAIL: {contributor.email}) (URL: {contributor.url})\n"
                else:
                    organizations_text += f"- {contributor.name}\n"
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

    def get_study_target(self):
        subjects = self.get_subjects()

        ds_id, ds_version = self.dandiset_id.split("/")
        dandiset = self.dandi_client.get_dandiset(ds_id, ds_version)
        dandiset_metadata = dandiset.get_raw_metadata()
        dandiset_title = dandiset_metadata.get("name", None)
        dandiset_description = dandiset_metadata.get("description", None)
        
        doi_title = self.get_title()
        doi_abstract = self.get_abstract()

        if subjects and len(subjects) > 0:
            expert_prompt = f"You are an expert in the following subjects: {', '.join(subjects)}"
        else:
            expert_prompt = ""

        system_prompt = "You are a neuroscience expert and you are interested in developing a study target (objective or specific questions of the study) for a given dataset."

        prompt = f"""
        {expert_prompt}
        Given a dataset title, description, DOI title, and abstract, your task is to succinctly discern the study target, encompassing both the overarching goal and specific questions. 
        In instances where any of the four components is missing/None, offer insights based on available information.
        Present your response in a short and concise one-sentence format and ensure any essential subject or NER related keywords are present.
        Start all your responses with the following: The study target is to...
        -----
        Dataset Title: {dandiset_title if dandiset_title else "None"}
        Dataset Description: {dandiset_description if dandiset_description else "None"}
        -----
        Related DOI Title: {doi_title if doi_title else "None"}
        Related DOI Abstract: {doi_abstract if doi_abstract else "None"}
        -----
        """

        MODEL = "gpt-3.5-turbo"
        MAX_TOKENS = 100
        completion = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.0,
        )
        self.study_target = completion.choices[0].message.content
        return self.study_target
    

    def stringify_study_target(self):
        study_target = self.get_study_target()
        text = f"STUDY TARGET:\n{study_target}\n"
        return text
    
    
    def get_keywords(self, study_target_test, type="keybert"):
        if study_target_test:
            study_target = study_target_test
        else:
            if self.study_target:
                study_target = self.study_target
            else:
                study_target = self.get_study_target()

        if type == "keybert":
            keywords = self.get_keywords_keybert(study_target)
        elif type == "llm":
            keywords = self.get_keywords_llm(study_target)
        else:
            print("Invalid keyword extraction type.")
            return None

        return keywords


    def get_keywords_keybert(self, study_target: str = None):
        kw_model = KeyBERT()
        keywords = kw_model.extract_keywords(
            study_target,
            keyphrase_ngram_range=(1, 4),
            top_n=NUM_KEYWORDS,
            stop_words=None,
        )
        return [kw[0] for kw in keywords]


    def get_keywords_llm(self, study_target: str = None):
        system_prompt = "You are a neuroscience expert and you are interested in extracting important/related entities from a study target text."
        
        prompt = f"""
        Here is the study target (objective and/or question) for a given neurophysiological dataset:
        {study_target}
        -----
        Analyze the study target and return a ranked list of the top {NUM_KEYWORDS} most relevant entities (or grouped entities) ordered from most relevant to least relevant.
        If a word or noun does not seem related enough to be a entity, do not include it in the list.
        The format of the output list should be the {NUM_KEYWORDS} entities in a one-row CSV (comma-separated values) format.
        """

        MODEL = "gpt-3.5-turbo"
        completion = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        choices = completion.choices[0].message.content
        keywords = choices.split(", ")
        return keywords


    def stringify_keywords(self):
        keywords = self.get_keywords_llm()

        text = "KEYWORDS:\n"
        if keywords:
            text += ", ".join(keywords)
        else:
            text += "None\n"

        return text
    

    # NOTE: may not be needed
    def get_references(self):
        """Related resources (relation: dcite:isDescribedBy)"""
        references = self.works["reference"]
        return references


    def stringify(self):
        contributors = self.stringify_contributors()
        study_target = self.stringify_study_target()
        keywords = self.stringify_keywords()

        return f"\n{contributors}\n{study_target}\n{keywords}"


    def get_title(self) -> str:
        return self.works.get("title", None)
    

    def get_abstract(self) -> str:
        return self.works.get("abstract", None)
    

    def get_subjects(self) -> list[str]:
        return self.works.get("subject", None)


