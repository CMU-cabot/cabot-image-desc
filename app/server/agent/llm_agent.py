# Copyright (c) 2024  Carnegie Mellon University and Miraikan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import asyncio
import base64
import cv2
import json
import os
from typing import (
    Generic,
    List,
    Optional,
    TypeVar,
)
from ollama import AsyncClient
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain.chat_models import init_chat_model

from .llm_agent_template import (
    SYSTEM_MESSAGE,
    SENTENCE_ATOMOSPHERE_SHORT,
    SENTENCE_ATOMOSPHERE,
    SCENE_DESCRIPTION_STYLE_SHORT,
    SCENE_DESCRIPTION_STYLE,
    DESCRIPTION_PROMPT_TEMPLATE,
    PAST_EXPLANATIONS_TEMPLATE,
    STOP_REASON_PROMPT_TEMPLATE,
    SINGLE_IMAGE_DESCRIPTION_PROMPT_TEMPLATE,
    SUMMARIZATION_PROMPT_TEMPLATE,
    STOP_REASON_IMAGE_DESCRIPTION_PROMPT_TEMPLATE,
    STOP_REASON_SUMMARIZATION_PROMPT_TEMPLATE,
)


USE_PAST_EXPLANATIONS = os.environ.get("USE_PAST_EXPLANATIONS", "false").lower() == "true"

# langchain and ollama
LLM_AGENT = os.environ.get("LLM_AGENT")
AGENT_VLM = os.environ.get("AGENT_VLM", "")
AGENT_LLM = os.environ.get("AGENT_LLM", "")
# langchain-ibm
WATSONX_URL = os.environ.get("WATSONX_URL")
WATSONX_API_KEY = os.environ.get("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.environ.get("WATSONX_PROJECT_ID")


ContentType = TypeVar("ContentType")


# langchain structured output class converted from dict
class StructuredOutputResponse(BaseModel, Generic[ContentType]):
    raw: BaseMessage
    parsed: Optional[ContentType]
    parsing_error: Optional[str]


class LangChainAgentResponse(BaseModel, Generic[ContentType]):
    intermediate_responses: Optional[List[BaseMessage]]
    response: StructuredOutputResponse[ContentType]


class TranslatedDescription(BaseModel):
    description: str
    translated: str
    lang: str

    def to_dict(self):
        return self.model_dump()


def determine_sentence_length(request_length, distance_to_travel):
    """
    input
    request_length: int. length of the request from user from 0 - 2, 0 being the shortest, 1 being the middle and 2 being the longest
    distance_to_travel: float, remaining distance to travel to the location in meters

    output
    sentence_length: int, length of the sentence to generate
    """

    sentence_num_to_add = request_length

    if distance_to_travel < 10:
        if sentence_num_to_add == 2:
            sentence_num_to_add = 1
        else:
            sentence_num_to_add = 0  # we dont want to add more than 1 sentence if the distance is less than 10 meters
        return 1 + sentence_num_to_add
    elif distance_to_travel < 25:
        return 2 + sentence_num_to_add
    else:  # distance longer than 25 meters
        return 3 + sentence_num_to_add


def sentence_atmosphere_in_Japanese(sentence_length: int) -> str:
    if sentence_length <= 2:
        return SENTENCE_ATOMOSPHERE_SHORT
    else:
        return SENTENCE_ATOMOSPHERE


def determine_scene_description_style(sentence_length: int, force_use_default_style: bool = True) -> str:
    scene_desc_style = SCENE_DESCRIPTION_STYLE
    if force_use_default_style:
        return scene_desc_style
    else:
        if sentence_length < 3:
            scene_desc_style = SCENE_DESCRIPTION_STYLE_SHORT
    return scene_desc_style


def construct_prompt_for_image_description(sentence_length=3,
                                           front="",
                                           right="",
                                           left="",
                                           past_explanations="",
                                           image_tags="",
                                           lang="ja",
                                           ):
    if front != "":
        front = front.replace("\n", " ")
    if right != "":
        right = right.replace("\n", " ")
    if left != "":
        left = left.replace("\n", " ")

    prompt_template = DESCRIPTION_PROMPT_TEMPLATE

    sentence_atmosphere = sentence_atmosphere_in_Japanese(sentence_length)
    scene_desc_style = determine_scene_description_style(sentence_length, force_use_default_style=True)

    prompt = prompt_template.format(front=front,
                                    right=right,
                                    left=left,
                                    min_sentence_length=sentence_length,
                                    max_sentence_length=sentence_length + 1,
                                    image_tags=image_tags,
                                    sentence_atmosphere=sentence_atmosphere,
                                    scene_description_style=scene_desc_style,
                                    lang=lang,
                                    )

    if USE_PAST_EXPLANATIONS and past_explanations:
        prompt += PAST_EXPLANATIONS_TEMPLATE.format(past_explanations=past_explanations)

    return prompt


class StopReason(BaseModel):
    pedestrian_info: str
    object_info: str
    thought: str
    message: str
    translated: str
    lang: str

    def to_dict(self):
        return self.model_dump()


def construct_prompt_for_stop_reason(lang="ja"):
    prompt_template = STOP_REASON_PROMPT_TEMPLATE
    prompt = prompt_template.format(lang=lang)
    return prompt


class DummyClient:
    class DictToObject:
        def __init__(self, obj):
            self.obj = obj
            for key, value in obj.items():
                if isinstance(value, dict):
                    setattr(self, key, DummyClient.DictToObject(value))
                elif isinstance(value, list):
                    setattr(
                        self,
                        key,
                        [DummyClient.DictToObject(item) if isinstance(item, dict) else item for item in value],
                    )
                else:
                    setattr(self, key, value)

        def model_dump_json(self):
            return json.dumps(self.obj, ensure_ascii=False)

    async def chat(self, model, messages, max_tokens=None, format=None):
        if format is not None:
            result = DummyClient.DictToObject({
                "choices": [
                    {
                        "message": {
                            "content": "This is a dummy response.",
                        }
                    }
                ]
            })
            obj = {}
            for field in format.model_fields.keys():
                obj[field] = "dummy_value"
            parsed_obj = format.model_validate(obj)
            result.choices[0].message.parsed = parsed_obj
            return result
        else:
            return DummyClient.DictToObject({
                "choices": [
                    {
                        "message": {
                            "content": "This is a dummy response."
                        }
                    }
                ]
            })


class BaseAgent:
    def __init__(self):
        pass

    # Function to encode the image
    def encode_image(self, image):
        if os.path.exists(image):
            image = cv2.imread(image)
            image = cv2.resize(image, (960, 540))
        _, buffer = cv2.imencode('.jpg', image)
        image_bytes = buffer.tobytes()
        return base64.b64encode(image_bytes).decode('utf-8')

    def get_encoding(self, encoded_image):
        prefix = "data:image/jpeg;base64,"
        if encoded_image.startswith(prefix):
            encoded_image = encoded_image[len(prefix):]
        return f"{prefix}{encoded_image}"

    # Prepare image message content
    def get_encoded_image_message(self, encoded_image):
        encoding = self.get_encoding(encoded_image)
        return {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": encoding,
                    }
                }
            ]
        }

    def update_past_descriptions(self, description, lat, lng):
        self.past_descriptions.append({"description": description, "location": {"lat": lat, "lng": lng}})

    def construct_prompt_for_image_description(self,
                                               sentence_length=3,
                                               front="",
                                               right="",
                                               left="",
                                               past_explanations="",
                                               image_tags="",
                                               lang="ja",
                                               ):
        return construct_prompt_for_image_description(sentence_length,
                                                      front,
                                                      right,
                                                      left,
                                                      past_explanations,
                                                      image_tags,
                                                      lang,
                                                      )

    def construct_prompt_for_stop_reason(self, lang):
        return construct_prompt_for_stop_reason(lang)

    # Function to query with images
    async def query_with_images(self, prompt, images=[], max_tokens=3000, response_format=None):
        pass


class OllamaAgent(BaseAgent):
    def __init__(self, model=AGENT_VLM):
        self.llm_agent = LLM_AGENT
        if self.llm_agent == "dummy_ollama":
            self.client = DummyClient()
        elif self.llm_agent == "ollama":
            self.client = AsyncClient()
        else:
            raise ValueError("Please set valid LLM agent.")
        self.model = model

        if self.model == "":
            raise ValueError("Please set AGENT_VLM")

        self.past_descriptions = []

    # Function to query with images
    async def query_with_images(self, prompt, images=[], max_tokens=3000, response_format=None):
        # Preparing the content with the prompt and images
        messages = [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            }
        ]

        images_content = []
        for image in images:
            if 'image_uri' in image:
                image_uri = image['image_uri']
                images_content.append(image_uri.split(",")[1])  # bytes

        messages = []
        messages.append(
            {
                "role": "user",
                "content": prompt,
                "images": images_content,
            }
        )

        query = {
            "model": self.model,
            "messages": messages
        }
        # Making the API call
        try:
            if response_format:
                query2 = {**query, **{"format": response_format.model_json_schema()}}
                response = await self.client.chat(**query2)
            else:
                response = await self.client.chat(**query)
        except Exception as e:
            response = DummyClient.DictToObject(
                {
                    "error": str(e),
                    "choices": [
                        {
                            "message": {
                                "parsed": {
                                    "description": "dummy",
                                    "message": "dummy",
                                    "translated": "dummy",
                                    "lang": "dummy",
                                }
                            }
                        }
                    ],
                }
            )
        return (response, query)


class LangChainAgent(BaseAgent):
    def __init__(self, model=AGENT_VLM):
        self.llm_agent = LLM_AGENT
        if self.llm_agent == "dummy_langchain":
            self.client = DummyClient()
        elif self.llm_agent == "langchain":
            parameters = {
                "temperature": 0.0,
                "max_tokens": 3000,
            }
            self.client = init_chat_model(
                model=model,
                url=WATSONX_URL,
                apikey=WATSONX_API_KEY,
                project_id=WATSONX_PROJECT_ID,
                params=parameters,
            )
        else:
            raise ValueError("Please set valid LLM agent.")
        self.model = model

        if self.model == "":
            raise ValueError("Please set AGENT_VLM")

        self.past_descriptions = []

    # Function to query with images
    async def query_with_images(self, prompt, images=[], max_tokens=3000, response_format=None):
        print("query_with_images")
        # Preparing the content with the prompt and images
        messages = [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            }
        ]

        content = []
        for image in images:
            if 'image_uri' in image:
                image_uri = image['image_uri']
                content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image_uri,
                            },
                        })
        content.append(
            {
                "type": "text",
                "text": prompt
            }
        )

        messages.append(
            {
                "role": "user",
                "content": content
            }
            # HumanMessage(
            #     content=content
            # )
        )

        query = {
            "model": self.model,
            "messages": messages
        }
        # Making the API call
        try:
            if response_format:
                response = await self.client.with_structured_output(
                                response_format,
                                include_raw=True
                            ).ainvoke(messages)
                response = StructuredOutputResponse(
                                raw=response["raw"],
                                parsed=response["parsed"],
                                parsing_error=str(response["parsing_error"]),
                            )
            else:
                response = await self.client.ainvoke(messages)
        except Exception as e:
            response = DummyClient.DictToObject(
                {
                    "error": str(e),
                    "choices": [
                        {
                            "message": {
                                "parsed": {
                                    "description": "dummy",
                                    "message": "dummy",
                                    "translated": "dummy",
                                    "lang": "dummy",
                                }
                            }
                        }
                    ],
                }
            )
        return (response, query)


class Base2StepAgent(BaseAgent):
    # data class
    class Prompt(BaseModel):
        single_image_description_prompt: str
        summarization_prompt_template: str
        summarization_prompt: str
        image_tags: str

    def construct_prompt_for_image_description(self,
                                               sentence_length=3,
                                               front="",
                                               right="",
                                               left="",
                                               past_explanations="",
                                               image_tags="",
                                               lang="ja",
                                               ):

        if front != "":
            front = front.replace("\n", " ")
        if right != "":
            right = right.replace("\n", " ")
        if left != "":
            left = left.replace("\n", " ")

        sentence_atmosphere = sentence_atmosphere_in_Japanese(sentence_length)
        scene_desc_style = determine_scene_description_style(sentence_length, force_use_default_style=True)

        single_image_description_prompt = \
            SINGLE_IMAGE_DESCRIPTION_PROMPT_TEMPLATE.format(
                                    min_sentence_length=sentence_length,
                                    max_sentence_length=sentence_length + 1,
                                    sentence_atmosphere=sentence_atmosphere,
                                    scene_description_style=scene_desc_style,
                                    )

        summarization_prompt_template = \
            SUMMARIZATION_PROMPT_TEMPLATE.format(
                front=front,
                right=right,
                left=left,
                min_sentence_length=sentence_length,
                max_sentence_length=sentence_length + 1,
                image_descriptions="{image_descriptions}",
                sentence_atmosphere=sentence_atmosphere,
                scene_description_style=scene_desc_style,
                lang=lang,
            )

        if USE_PAST_EXPLANATIONS and past_explanations:
            summarization_prompt_template += \
                PAST_EXPLANATIONS_TEMPLATE.format(
                    past_explanations=past_explanations
                )

        prompt_data = Base2StepAgent.Prompt(
            single_image_description_prompt=single_image_description_prompt,
            summarization_prompt_template=summarization_prompt_template,
            summarization_prompt="",
            image_tags=image_tags,
        )

        return prompt_data.model_dump()

    def construct_prompt_for_stop_reason(self, lang):
        single_image_description_prompt = \
            STOP_REASON_IMAGE_DESCRIPTION_PROMPT_TEMPLATE.format()

        summarization_prompt_template = \
            STOP_REASON_SUMMARIZATION_PROMPT_TEMPLATE.format(
                lang=lang,
                image_descriptions="{image_descriptions}",
                )

        prompt_data = Base2StepAgent.Prompt(
            single_image_description_prompt=single_image_description_prompt,
            summarization_prompt_template=summarization_prompt_template,
            summarization_prompt="",
            image_tags="front image description\n",
        )

        return prompt_data.model_dump()


class Ollama2StepAgent(Base2StepAgent):
    def __init__(self, model=AGENT_VLM, language_model=AGENT_LLM):
        self.llm_agent = LLM_AGENT
        if self.llm_agent == "dummy_ollama":
            self.client = DummyClient()
        elif self.llm_agent in ["ollama", "ollama-2step"]:
            self.client = AsyncClient()
        else:
            raise ValueError("Please set valid LLM agent.")
        self.model = model
        self.language_model = language_model

        if self.model == "":
            raise ValueError("Please set AGENT_VLM.")
        if self.language_model == "":
            raise ValueError("Please set AGENT_LLM.")

        self.past_descriptions = []

    # Function to query with images
    async def query_with_images(self, prompt, images=[], max_tokens=3000, response_format=None):
        # convert from dict
        prompt_instance = Base2StepAgent.Prompt(**prompt)

        # image description
        messages = [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            }
        ]

        # create tasks
        queries = []
        desc_tasks = []
        for image in images:
            if 'image_uri' in image:
                image_uri = image['image_uri']
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_MESSAGE,
                    },
                    {
                        "role": "user",
                        "content": prompt_instance.single_image_description_prompt,
                        "images": [
                            image_uri.split(",")[1]  # byte
                        ]
                    }
                ]
                query = {
                    "model": self.model,
                    "messages": messages,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": max_tokens,
                    },
                }
                queries.append(query)
                desc_tasks.append(self.client.chat(**query))

        # API call
        desc_responses = []
        try:
            if len(desc_tasks) > 0:
                desc_responses = await asyncio.gather(*desc_tasks)
        except Exception as e:
            response = DummyClient.DictToObject(
                {
                    "error": str(e),
                    "choices": [
                        {
                            "message": {
                                "parsed": {
                                    "description": "dummy",
                                    "message": "dummy",
                                    "translated": "dummy",
                                    "lang": "dummy",
                                }
                            }
                        }
                    ],
                }
            )

        # summarization
        image_tags_splitted = prompt_instance.image_tags.split("\n")

        # prompt_concat = prompt.summarization_prompt1
        image_descriptions_str = ""
        for idx, desc_resp in enumerate(desc_responses):
            response_content = desc_resp.message.content.strip()
            image_tag = image_tags_splitted[idx]
            image_descriptions_str += image_tag + ": " + response_content + "\n"

        prompt_concat = prompt_instance.summarization_prompt_template.format(
            image_descriptions=image_descriptions_str
            )

        # update reformatted prompt
        prompt["summarization_prompt"] = prompt_concat

        messages = [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            },
            {
                "role": "user",
                "content": prompt_concat,
            }
        ]

        query = {
            "model": self.language_model,
            "messages": messages,
            "options": {
                "temperature": 0.0,
                "num_predict": max_tokens,
            },
        }

        # Making the API call
        try:
            if response_format:
                query2 = {**query,
                          **{"format": response_format.model_json_schema()}
                          }
                response = await self.client.chat(**query2)
            else:
                response = await self.client.chat(**query)
        except Exception as e:
            response = DummyClient.DictToObject(
                {
                    "error": str(e),
                    "choices": [
                        {
                            "message": {
                                "parsed": {
                                    "description": "dummy",
                                    "message": "dummy",
                                    "translated": "dummy",
                                    "lang": "dummy",
                                }
                            }
                        }
                    ],
                }
            )
        return (response, query)


class LangChain2StepAgent(Base2StepAgent):
    def __init__(self, model=AGENT_VLM, language_model=AGENT_LLM):
        self.llm_agent = LLM_AGENT
        if self.llm_agent == "langchain-2step":
            pass
        else:
            raise ValueError("Please set valid LLM agent.")
        self.model = model
        self.language_model = language_model

        if self.model == "":
            raise ValueError("Please set AGENT_VLM.")
        if self.language_model == "":
            raise ValueError("Please set AGENT_LLM.")

        parameters = {
                "temperature": 0.0,
                "max_tokens": 3000,
            }

        self.vlm_client = init_chat_model(
                model=self.model,
                url=WATSONX_URL,
                apikey=WATSONX_API_KEY,
                project_id=WATSONX_PROJECT_ID,
                params=parameters,
            )

        self.llm_client = init_chat_model(
                model=self.language_model,
                url=WATSONX_URL,
                apikey=WATSONX_API_KEY,
                project_id=WATSONX_PROJECT_ID,
                params=parameters,
            )

        self.past_descriptions = []

    # Function to query with images
    async def query_with_images(self, prompt, images=[], max_tokens=3000, response_format=None):
        # convert from dict
        prompt_instance = Base2StepAgent.Prompt(**prompt)

        # create tasks
        desc_queries = []
        desc_tasks = []
        for image in images:
            if 'image_uri' in image:
                image_uri = image['image_uri']
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_MESSAGE,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_uri,
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt_instance.single_image_description_prompt,
                            }
                        ]
                    }
                ]
                desc_query = {
                    "model": self.model,
                    "messages": messages,
                }
                desc_queries.append(desc_query)
                desc_tasks.append(self.vlm_client.ainvoke(messages))

        # API call
        desc_responses = []
        try:
            if len(desc_tasks) > 0:
                desc_responses = await asyncio.gather(*desc_tasks)
        except Exception as e:
            response = DummyClient.DictToObject(
                {
                    "error": str(e),
                    "choices": [
                        {
                            "message": {
                                "parsed": {
                                    "description": "dummy",
                                    "message": "dummy",
                                    "translated": "dummy",
                                    "lang": "dummy",
                                }
                            }
                        }
                    ],
                }
            )

        # summarization
        image_tags_splitted = prompt_instance.image_tags.split("\n")

        # prompt_concat = prompt.summarization_prompt1
        image_descriptions_str = ""
        for idx, desc_resp in enumerate(desc_responses):
            response_content = desc_resp.content.strip()  # AIMessage.content
            image_tag = image_tags_splitted[idx]
            image_descriptions_str += image_tag + ": " + response_content + "\n"

        prompt_concat = prompt_instance.summarization_prompt_template.format(
            image_descriptions=image_descriptions_str
            )

        # update reformatted prompt
        prompt["summarization_prompt"] = prompt_concat

        messages = [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            },
            {
                "role": "user",
                "content": prompt_concat,
            }
        ]

        summarization_query = {
            "model": self.language_model,
            "messages": messages,
        }

        query = {
            "image_description": desc_queries,
            "summarization": summarization_query,
        }

        # Making the API call
        try:
            if response_format:
                response = await self.llm_client.with_structured_output(
                                response_format,
                                include_raw=True
                            ).ainvoke(messages)
                response = StructuredOutputResponse(
                                raw=response["raw"],
                                parsed=response["parsed"],
                                parsing_error=str(response["parsing_error"]),
                            )
                response = LangChainAgentResponse(
                    intermediate_responses=desc_responses,
                    response=response,
                )
            else:
                response = await self.llm_client.ainvoke(messages)
        except Exception as e:
            response = DummyClient.DictToObject(
                {
                    "error": str(e),
                    "choices": [
                        {
                            "message": {
                                "parsed": {
                                    "description": "dummy",
                                    "message": "dummy",
                                    "translated": "dummy",
                                    "lang": "dummy",
                                }
                            }
                        }
                    ],
                }
            )
        return (response, query)
