import re
import google.generativeai as genai
import os
import deployment.synthetic_data as synthetic_data

MY_API_KEY = os.getenv("API_KEY")
genai.configure(api_key=MY_API_KEY)
store_df = synthetic_data.synthetic_data_gen(num_rows= 1000)


def format_code_blocks(text):
  """Formats code blocks within "Action X:" sections by adding ```python.

  Args:
    text: The input string.

  Returns:
    The modified string with formatted code blocks.
  """

  pattern = r"(Action \d+):\n(.*?)(?=Thought \d+)"
  replacement = lambda m: f"{m.group(1)}:\n```python\n{m.group(2).strip()}\n```"
  return re.sub(pattern, replacement, text, flags=re.DOTALL)


# ## The ReAct Agent Pipeline
# Define the ReAct class for interacting with the Gemini model

class ReAct:
  def __init__(self, model: str, ReAct_prompt: str):
    """
    Initializes the ReAct agent, enabling the Gemini model to understand and
    respond to a 'Few-shot ReAct prompt'. This is achieved by mimicking the
    'function calling' technique, which allows the model to generate both
    reasoning steps and specific actions in an interleaved fashion.

    Args:
        model: name to the model.
        ReAct_prompt: ReAct prompt.
    """
    self.model = genai.GenerativeModel(model)
    self.chat = self.model.start_chat(history=[])
    self.should_continue_prompting = True
    self._search_history: list[str] = []
    self._search_urls: list[str] = []
    self._prompt = ReAct_prompt

  @property
  def prompt(self):
    return self._prompt

  @classmethod
  def add_method(cls, func):
    setattr(cls, func.__name__, func)

  @staticmethod
  def clean(text: str):
    """Helper function for responses."""
    text = text.replace("\n", " ")
    return text

# %%
#@title Search
@ReAct.add_method
def search(self, query: str):
    """
    Perfoms search on `query` via a given dataframe.

    Args:
        query: Search parameter to query the dataframe.

    Returns:
        observation: Summary of the search finding for `query` if found.
    """
    query = query.strip()
    try:
      ## instruct the model to generate python code based on the query
      observation = self.model.generate_content("""
        Question: write a python code without any explination on question: {}.
        Please do not name the final output.
        Only return the value of the output without print function.

        Answer:
        """.format(query))

      observation = observation.text
      result = eval(observation.replace('```python', '').replace('```', ''))

      ## keep search history
      self._search_history.append(query)
      self._search_results.append(result)
    except:
      observation = f'Could not find ["{query}"].'

    return observation

# %%
#@title Execute

@ReAct.add_method
def execute(self, code_phrase: str):
    """
    Execute `code_phrase` from search and return the result.

    Args:
        phrase: The code snippit to look up the values of intested.

    Returns:
        code_result: Result after executing the `code_phrase` .
    """

    code_result = {}
    try:
      exec(code_phrase.replace('```python', '').replace('```', ''), globals(), code_result)
    except:
      code_result = f'Could not execute code["{code_phrase}"]'
    return code_result

# %%
#@title Finish

@ReAct.add_method
def finish(self, _):
  """
  Stops the question-answering process when the model generates a `<finish>`
  token. This is achieved by setting the `self.should_continue_prompting` flag
  to `False`, which signals to the agent that the final answer has been reached.
  """
  self.should_continue_prompting = False

# %%
#@title Function calling

@ReAct.add_method
def __call__(self, user_question, max_calls: int=10, **generation_kwargs):
  """
  Starts multi-turn conversation with the LLM models, using function calling
  to interact with external tools.

  Args:
      user_question: The initial question from the user.
      max_calls: The maximum number of calls to the model before ending the
          conversation.
      generation_kwargs: Additional keyword arguments for text generation,
          such as temperature and max_output_tokens. See
          `genai.GenerativeModel.GenerationConfig` for details.
  Returns:
      responses: The responses from the model.

  Raises:
      AssertionError: if max_calls is not between 1 and 10
  """
  responses = ''

  # set a higher max_calls for more complex task.
  assert 0 < max_calls <= 10, "max_calls must be between 1 and 10"

  if len(self.chat.history) == 0:
    model_prompt = 'Based on the dataset from store_df, ' + self.prompt + user_question
  else:
    model_prompt = 'Based on the dataset from store_df, ' + user_question

  # stop_sequences for the model to imitate function calling
  callable_entities = ['</search>', '</execute>', '</finish>']
  generation_kwargs.update({'stop_sequences': callable_entities})

  self.should_continue_prompting = True
  for idx in range(max_calls):

    self.response = self.chat.send_message(
        content=[model_prompt],
        generation_config=generation_kwargs,
        stream=False)

    for chunk in self.response:
      print(chunk.text.replace("tool_code", '').replace("`", ''), end='\n')

    response_cmd = self.chat.history[-1].parts[-1].text
    responses = responses + response_cmd

    try:
      cmd = re.findall(r'<(.*)>', response_cmd)[-1]
      query = response_cmd.split(f'<{cmd}>')[-1].strip()

      # call to appropriate function
      observation = self.__getattribute__(cmd)(query)

      if not self.should_continue_prompting:
        break

      stream_message = f"\nObservation {idx + 1}\n{observation}"

      # send function's output as user's response to continue the conversation
      model_prompt = f"<{cmd}>{query}</{cmd}>'s Output: {stream_message}"
    except (IndexError, AttributeError) as e:
      model_prompt = "Please try to generate as instructed by the prompt."
  final_answer = (
    self.chat.history[-1].parts[-1].text.split('<finish>')[-1].strip()
  )

  responses = format_code_blocks(responses)
  responses = re.sub(r'Thought (\d+):', r'\n#### Thought \1:\n', responses)
  responses = re.sub(
      r'Observation (\d+):', r'\n#### Observation \1:\n', responses
  )
  responses = re.sub(r'Action (\d+):', r'\n#### Action \1:\n', responses)

  return (responses, final_answer)


