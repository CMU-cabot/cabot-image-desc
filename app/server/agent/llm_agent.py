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
    Any,
    List,
    Generic,
    Optional,
    TypedDict,
    TypeVar,
    Union,
)
from ollama import AsyncClient
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain.chat_models import init_chat_model


USE_PAST_EXPLANATIONS = os.environ.get("USE_PAST_EXPLANATIONS", "false").lower() == "true"

# langchain and ollama
LLM_AGENT = os.environ.get("LLM_AGENT")
AGENT_VLM = os.environ.get("AGENT_VLM", "")
AGENT_LLM = os.environ.get("AGENT_LLM", "")
# langchain
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER")
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


class TranslatedDescription(BaseModel):
    description: str
    translated: str
    lang: str

    def to_dict(self):
        return self.model_dump()


DESCRIPTION_PROMPT_TEMPLATE = """
# 指示
与えられた画像について説明してdescriptionにいれます。
複数の画像は以下の向きに対応しています。
{image_tags}

画像に加えて、専門家によって事前に作成された、そのカメラ座標に関連する説明文も提供されることがあります。
この説明文も、説明文を生成する際に利用してください。ただし、説明文が提供されていることが聞き手には分からないように、あくまで画像からその情報を直接得たかのように説明してください。
なお、説明文の方向は相対的なものであり、例えば右の説明において左に関する説明がされている場合、それは前方向の説明になります。

{front}
{right}
{left}

また、descriptionを言語コード「{lang}」にしたがって翻訳しtranslatedにいれます。その時使ったコードをlangにいれます。
{lang}がjaの時はdescriptionをそのままtranslatedにいれます。

## 必ずすべきこと
1. {sentence_atmosphere}説明すること。全体で丁度{min_sentence_length}文の説明になるようにしてください。
2  そのまま音声エンジンで読み上げられるので、特殊記号は使わないこと。一まとまりの文章で説明する事。
3. 丁寧語を使うこと。{scene_description_style}
4. 各方向ごとに、画像から得られるリアルタイムなその場の情報を先に説明してから、テキストで与えられた情報も必ず説明してください。【重要】タグのついた情報や、看板や施設・設備に関する情報が与えられた場合、必ず具体的に説明に含めてください。
5. 横断歩道や信号機などが存在する場合にのみ、それらについて言及してください。存在しない場合は、横断歩道や信号機については決して出力しないでください。

## 絶対にしてはいけないこと
6. 説明はユーザにそのまま読み上げられるので「画像は」「視点」「重要」「追加情報」「説明文」など、説明を聞くユーザにとって不自然な言葉は絶対に用いないでください。特に「画像」「重要」という言葉は使わないでください。
7. 日本人にとって分かりにくい英語表現（例：ビルディング等）は避けてください。
8. 後方に関する説明はしないでください。

"""

SINGLE_IMAGE_DESCRIPTION_PROMPT_TEMPLATE = """
# 指示
与えられた画像について説明してください。

## 必ずすべきこと
1. {sentence_atmosphere}説明すること。全体で丁度{min_sentence_length}文の説明になるようにしてください。
2  そのまま音声エンジンで読み上げられるので、特殊記号は使わないこと。一まとまりの文章で説明する事。
3. 丁寧語を使うこと。{scene_description_style}
4. 横断歩道や信号機などが存在する場合にのみ、それらについて言及してください。存在しない場合は、横断歩道や信号機については決して出力しないでください。

## 絶対にしてはいけないこと
5. 説明はユーザにそのまま読み上げられるので「画像は」「視点」「重要」「追加情報」「説明文」など、説明を聞くユーザにとって不自然な言葉は絶対に用いないでください。特に「画像」「重要」という言葉は使わないでください。
6. 後方に関する説明はしないでください。
"""

SUMMARIZATION_PROMPT_TEMPLATE = """
# 指示
複数のリアルタイム画像から得られた説明文を提供するので、指示に従って要約し、descriptionにいれます。

{image_descriptions}

リアルタイム画像に加えて、専門家によって事前に作成された、そのカメラ座標に関連する説明文も提供されることがあります。
この説明文も、説明文を生成する際に利用してください。ただし、説明文が提供されていることが聞き手には分からないように、あくまで画像からその情報を直接得たかのように説明してください。
なお、説明文の方向は相対的なものであり、例えば右の説明において左に関する説明がされている場合、それは前方向の説明になります。

{front}
{right}
{left}

また、descriptionを言語コード「{lang}」にしたがって翻訳しtranslatedにいれます。その時使ったコードをlangにいれます。
{lang}がjaの時はdescriptionをそのままtranslatedにいれます。

## 必ずすべきこと
1. {sentence_atmosphere}説明すること。全体で丁度{min_sentence_length}文の説明になるようにしてください。
2  そのまま音声エンジンで読み上げられるので、特殊記号は使わないこと。一まとまりの文章で説明する事。
3. 丁寧語を使うこと。{scene_description_style}
4. 各方向ごとに、画像から得られるリアルタイムなその場の情報を先に説明してから、テキストで与えられた情報も必ず説明してください。【重要】タグのついた情報や、看板や施設・設備に関する情報が与えられた場合、必ず具体的に説明に含めてください。
5. 横断歩道や信号機などが存在する場合にのみ、それらについて言及してください。存在しない場合は、横断歩道や信号機については決して出力しないでください。

## 絶対にしてはいけないこと
6. 説明はユーザにそのまま読み上げられるので「画像は」「視点」「重要」「追加情報」「説明文」など、説明を聞くユーザにとって不自然な言葉は絶対に用いないでください。特に「画像」「重要」という言葉は使わないでください。
7. 日本人にとって分かりにくい英語表現（例：ビルディング等）は避け、翻訳した単語を使用してください。
8. 後方に関する説明はしないでください。
"""

PAST_EXPLANATIONS_TEMPLATE = """
## 過去に説明した内容
過去にあなたは以下の内容を説明しました。
これからあなたが生成する説明は、過去に説明した内容は削除してください。
削除した場合、全体の説明は多少短くても構いません。

{past_explanations}
"""


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
        return "とても簡潔に、各物体の名前と位置だけ"
    else:
        return "各物体の詳細や位置、推測できることや主観的な形容詞を交えつつ詳しく"


def determine_scene_description_style(sentence_length: int, force_use_default_style: bool = True) -> str:
    scene_desc_style = "ガイドさんのように「全体的には」「左手には」「右手には」「前方には」など丁寧な言葉を使ってください。必ず全体の要約から始め、左側、正面、右側の順番で説明してください。"
    if force_use_default_style:
        return scene_desc_style
    else:
        if sentence_length < 3:
            scene_desc_style = "ガイドさんのように「前方には」「左右には」など丁寧な言葉を使ってください。必ず前方、左右の順番で説明してください。説明は可能な限り短く、端的かつ具体的にしてください。"
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


STOP_REASON_PROMPT_TEMPLATE = """
# 指示
視覚障害者を案内しているロボットが案内中に止まってしまいました。
その理由をロボットの正面画像を参照しつつ説明してください。
まず最初に、すぐ近くにいる人の人数を数えて、どの方向を向いて何をしてるかを把握してください（pedestrian_info）。
遠くにしか人がいない場合は「遠くに人が居ます」、全く人がいない場合は「人はいません」と答えてください。
その次に近くの障害物の数とそれらの種類を把握してください（object_info）。障害物がない場合は「障害物はありません」と答えてください。
thoughtには、pedestrian_infoとobject_infoで、近くに人や障害物がある場合、ロボットが止まった理由とどんなことをユーザに伝えるべきかを考えてください。
最後に、その情報を元に、ロボットが止まった具体的な理由を説明してください（message）。messageは直接ユーザに読み上げる内容です。

# 翻訳（必須）
また、messageを言語コード「{lang}」にしたがって翻訳しtranslatedにいれます。その時使ったコードをlangにいれます。
{lang}がjaの時はdescriptionをそのままtranslatedにいれます。

## ルール
1. 日本語で簡潔に述べること。
2. 丁寧語を使うこと。
3. まずは、「XX（理由）なため、停止しました」というフォーマットで答えてください。追加で情報を提示する必要がある場合は、その後に続けて説明してください。
4. ルール3のXX（理由）は可能な限り具体的な理由を記載してください。ダメな例: 「前方に人がいるため」（いるだけだとロボットが止まる理由にはならない）、良い例:「前方に人がいて道を塞いでいるため」「人が前方で談話していて道を塞いでいるため」「人が前方を横切ったため」
5. messageではどの位置に人がいるか、どんな人（大人、子供、性別など）がいるか、どの位置に障害物があるかを説明してください。また、人が何をしているか、障害物が何かを説明してください。例:「**右側から**女性が**前方を横切ったため**」「人が**右前**で**キオスクを操作しているため**」
6. 人と障害物が両方ある場合は近くて、ロボットの停止の主な原因となっている方について説明してください。
7. 横断歩道や信号機などが存在する場合にのみ、それらについて言及してください。存在しない場合は、横断歩道や信号機については決して出力しないでください。
8. 物体を参照する際、「何か」など曖昧な表現を使わないでください。具体的な物体名を使ってください。難しい場合はできる範囲でその形、どこにあるか、その色などを説明してください。
9. 止まった理由がわからない場合や前が開けていて、本来は進める状況の場合は「少々お待ちください」と答えて、必ず周囲の様子を説明してください。「ロボットが止まった理由がわかりません」など、ユーザが不安になるような回答はしないでください。例：「少々お待ちください。道は開けていて、右側に木製の展示があります。」
10. 日本人にとって分かりにくい英語表現（例：ビルディング等）は避けてください。
11. 説明はユーザにそのまま読み上げられるので「画像は」「視点」「重要」「追加情報」「説明文」や特殊記号など、説明を聞くユーザにとって不自然な言葉は絶対に用いないでください。特に「画像」「重要」という言葉は使わないでください。
12. 後方に関する説明はしないでください。
13. 止まった理由だけを説明すればいいので、不要な周囲の説明はしないでください。
14. 「可能性があります」など、推測を含む表現は使わないでください。
15. ユーザは受動的にロボットについて行くため、「少し右側を進むと通れます。」などの具体的な行動を促す表現は使わないでください。
16. ロボットのカメラの位置は低いので、近い人は足しか見えない可能性があります。近くの人を見逃さないでください。
"""

STOP_REASON_IMAGE_DESCRIPTION_PROMPT_TEMPLATE = """
# 指示
視覚障害者を案内しているロボットが案内中に止まってしまいました。
入力したロボットの正面画像から、その理由を説明するための情報を抽出してください。Please respond in English.

回答が必要な情報
- pedestrian_info: すぐ近くにいる人の人数を数えて、どの方向を向いて何をしてるかを把握してください。遠くにしか人がいない場合は「遠くに人が居ます」、全く人がいない場合は「人はいません」と答えてください。
- object_info: 近くの障害物の数とそれらの種類を把握してください。障害物がない場合は「障害物はありません」と答えてください。
"""

STOP_REASON_SUMMARIZATION_PROMPT_TEMPLATE = """
# 指示
視覚障害者を案内しているロボットが案内中に止まってしまいました。
ロボットの正面画像のimage descriptionを与えるので、指示に従って指定した形式で回答してください。

{image_descriptions}

# 指示
まず最初に、すぐ近くにいる人の人数を数えて、どの方向を向いて何をしてるかを把握してください（pedestrian_info）。
遠くにしか人がいない場合は「遠くに人が居ます」、全く人がいない場合は「人はいません」と答えてください。
その次に近くの障害物の数とそれらの種類を把握してください（object_info）。障害物がない場合は「障害物はありません」と答えてください。
thoughtには、pedestrian_infoとobject_infoで、近くに人や障害物がある場合、ロボットが止まった理由とどんなことをユーザに伝えるべきかを考えてください。
最後に、その情報を元に、ロボットが止まった具体的な理由を説明してください（message）。messageは直接ユーザに読み上げる内容です。

# 翻訳（必須）
また、messageを言語コード「{lang}」にしたがって翻訳しtranslatedにいれます。その時使ったコードをlangにいれます。
{lang}がjaの時はdescriptionをそのままtranslatedにいれます。

## ルール
1. 日本語で簡潔に述べること。
2. 丁寧語を使うこと。
3. まずは、「XX（理由）なため、停止しました」というフォーマットで答えてください。追加で情報を提示する必要がある場合は、その後に続けて説明してください。
4. ルール3のXX（理由）は可能な限り具体的な理由を記載してください。
5. messageではどの位置に人がいるか、どんな人（大人、子供、性別など）がいるか、どの位置に障害物があるかを説明してください。また、人が何をしているか、障害物が何かを説明してください。
6. 人と障害物が両方ある場合は近くて、ロボットの停止の主な原因となっている方について説明してください。
7. 横断歩道や信号機などが存在する場合にのみ、それらについて言及してください。存在しない場合は、横断歩道や信号機については決して出力しないでください。
8. 物体を参照する際、「何か」など曖昧な表現を使わないでください。具体的な物体名を使ってください。難しい場合はできる範囲でその形、どこにあるか、その色などを説明してください。
9. 止まった理由がわからない場合や前が開けていて、本来は進める状況の場合は「少々お待ちください」と答えて、必ず周囲の様子を説明してください。「ロボットが止まった理由がわかりません」など、ユーザが不安になるような回答はしないでください。
10. 日本人にとって分かりにくい英語表現（例：ビルディング等）は避けてください。
11. 説明はユーザにそのまま読み上げられるので「画像は」「視点」「重要」「追加情報」「説明文」や特殊記号など、説明を聞くユーザにとって不自然な言葉は絶対に用いないでください。特に「画像」「重要」という言葉は使わないでください。
12. 後方に関する説明はしないでください。
13. 止まった理由だけを説明すればいいので、不要な周囲の説明はしないでください。
14. 「可能性があります」など、推測を含む表現は使わないでください。
15. ユーザは受動的にロボットについて行くため、「少し右側を進むと通れます。」などの具体的な行動を促す表現は使わないでください。
16. ロボットのカメラの位置は低いので、近い人は足しか見えない可能性があります。近くの人を見逃さないでください。
"""


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
                "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
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
                model_provider=MODEL_PROVIDER,
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
        # Preparing the content with the prompt and images
        messages = [
            {
                "role": "system",
                "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
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
                "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
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
                        "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
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
                "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
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
                model_provider=MODEL_PROVIDER,
                model=self.model,
                url=WATSONX_URL,
                apikey=WATSONX_API_KEY,
                project_id=WATSONX_PROJECT_ID,
                params=parameters,
            )

        self.llm_client = init_chat_model(
                model_provider=MODEL_PROVIDER,
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
        queries = []
        desc_tasks = []
        for image in images:
            if 'image_uri' in image:
                image_uri = image['image_uri']
                messages = [
                    {
                        "role": "system",
                        "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
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
                query = {
                    "model": self.model,
                    "messages": messages,
                }
                queries.append(query)
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
                "content": "あなたは視覚障害者が周囲の状況を理解するための説明アシスタントです。"
            },
            {
                "role": "user",
                "content": prompt_concat,
            }
        ]

        query = {
            "model": self.language_model,
            "messages": messages,
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
