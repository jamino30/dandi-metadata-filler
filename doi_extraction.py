from clients.crossref import CrossRef
from clients.dandi import DandiClient
from clients.openai import OpenAIClient

from keybert import KeyBERT

import concurrent.futures


# num of keywords to be extracted from DOI
NUM_KEYWORDS = 10


class DOIExtraction:
    def __init__(self, doi: str, dandiset_id: str):
        # Crossref
        self.doi = doi.strip()
        self.crossref_client = CrossRef()
        self.doi_metadata = self.crossref_client.get_doi_metadata(self.doi)
        if not self.doi_metadata:
            raise ValueError("Invalid DOI provided.")

        # Dandi
        self.dandiset_id = dandiset_id.strip()
        if len(dandiset_id.split("/")) != 2:
            raise ValueError("Invalid Dandiset ID provided.")
        self.dandi_client = DandiClient()
        id, version = self.dandiset_id.split("/")
        self.dandiset_metadata = self.dandi_client.get_raw_metadata(id, version)
        if not self.dandiset_metadata:
            raise ValueError("Invalid Dandiset ID provided.")

        # OpenAI
        self.openai_client = OpenAIClient()

        self.study_target = None

    
    def get_contributors(self):
        contributors = self.crossref_client.get_contributors()
        if not contributors:
            return None
        
        dandischema_contributors = []
        with concurrent.futures.ThreadPoolExecutor() as exec:
            futures = []
            for contributor in contributors:
                futures.append(exec.submit(self._process_contributor, contributor))

            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    dandischema_contributors.append(future.result())

        return dandischema_contributors
    

    def _process_contributor(self, contributor):
        affiliations = self.crossref_client.get_author_affiliations(contributor)
        
        if any(key in contributor for key in ["ORCID", "family", "given"]):
            family_name, given_name = self.crossref_client.get_author_full_name(contributor)
            if not family_name or not given_name:
                return None
            else:
                name = f"{family_name.strip().title()}, {given_name.strip().title()}"

            orcid = self.crossref_client.get_author_orcid(contributor)
            if orcid:
                orcid = orcid.split("/")[-1]
                email, url = self.crossref_client.get_info_from_orcid(orcid)
            else:
                email, url = None, None
                
            # person
            schema = self.dandi_client.filled_person_schema(
                orcid=orcid,
                name=name,
                email=email,
                url=url,
                affiliation=affiliations,
            )
        else:
            # organization
            schema = self.dandi_client.filled_organization_schema(
                ror=None,
                name=contributor.get("name", None),
                email=None,
                url=None,
                role=None,
            )
        return schema
    

    def get_study_target(self):
        subjects = self.crossref_client.get_subjects()

        dandiset_name = self.dandi_client.get_dandiset_name()
        dandiset_description = self.dandi_client.get_dandiset_description()
        
        doi_title = self.crossref_client.get_title()
        doi_abstract = self.crossref_client.get_abstract()

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
        Dataset Title: {dandiset_name if dandiset_name else "None"}
        Dataset Description: {dandiset_description if dandiset_description else "None"}
        -----
        Related DOI Title: {doi_title if doi_title else "None"}
        Related DOI Abstract: {doi_abstract if doi_abstract else "None"}
        -----
        """

        MODEL = "gpt-3.5-turbo"
        MAX_TOKENS = 100
        self.study_target = self.openai_client.get_llm_response(
            system_prompt=system_prompt,
            user_prompt=prompt,
            model=MODEL,
            temperature=0.0,
            max_tokens=MAX_TOKENS
        )
        return self.study_target
    

    def get_keywords(self, study_target_test: str = None, type="llm"):
        if study_target_test:
            study_target = study_target_test
        else:
            study_target = self.study_target if self.study_target else self.get_study_target()

        if type == "keybert":
            keywords = self.get_keywords_keybert(study_target)
        elif type == "llm":
            keywords = self.get_keywords_llm(study_target)
        else:
            print("Invalid keyword extraction type.")
            return None

        return keywords
    

    def get_keywords_keybert(self, study_target: str):
        kw_model = KeyBERT()

        stop_words = None

        keywords = kw_model.extract_keywords(
            study_target,
            keyphrase_ngram_range=(1, 2),
            top_n=NUM_KEYWORDS,
            diversity=0.7,
            stop_words=stop_words,
        )
        return [kw[0] for kw in keywords]


    def get_keywords_llm(self, study_target: str):
        system_prompt = "You are a neuroscience expert and you are interested in extracting important/related entities from a study target text."
        
        prompt = f"""
        Here is the study target (objective and/or question) for a given neurophysiological dataset:
        {study_target}
        -----
        Analyze the study target and return a ranked list of the top {NUM_KEYWORDS} most relevant entities (or grouped entities) ordered from most relevant to least relevant.
        If a word or noun does not seem related enough to be a entity, do NOT include it in the list.
        The format of the output list should be the {NUM_KEYWORDS} entities in a SINGLE-row CSV (comma-separated values) format.
        """

        MODEL = "gpt-3.5-turbo"
        choices = self.openai_client.get_llm_response(
            system_prompt=system_prompt,
            user_prompt=prompt,
            model=MODEL,
            temperature=0.0,
        )
        keywords = choices.split(", ")
        return keywords
    
    
    def create_dandiset_structure(self):
        contributors = self.get_contributors()
        study_target = self.get_study_target()
        keywords = self.get_keywords()

        return {
            "contributors": contributors,
            "study_target": study_target,
            "keywords": keywords,
        }