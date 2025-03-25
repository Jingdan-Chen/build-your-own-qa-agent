"""React app."""

from dataclasses import fields
import types
from typing import Callable, cast, Generator, Literal

import mesop as me
import deployment.react as react
from datetime import datetime
import deployment.prompt as prompt

@me.stateclass
class FeedbackState:
  feedback: str = ""
  reason: str = ""
  ask_reason: bool = False


@me.stateclass
class State:
  input: str
  output: str
  textarea_key: int


@me.content_component
def header(
    *,
    style: me.Style | None = None,
    is_mobile: bool = False,
    max_width: int | None = 1000,
):
  """Creates a simple header component.

  Args:
    style: Override the default styles, such as background color, etc.
    is_mobile: Use mobile layout. Arranges each section vertically.
    max_width: Sets the maximum width of the header. Use None for fluid header.
  """
  default_flex_style = (
      _DEFAULT_MOBILE_FLEX_STYLE if is_mobile else _DEFAULT_FLEX_STYLE
  )
  if max_width and me.viewport_size().width >= max_width:
    default_flex_style = merge_styles(
        default_flex_style,
        me.Style(
            width=max_width, margin=me.Margin.symmetric(horizontal='auto')
        ),
    )

  # The style override is a bit hacky here since we apply the override styles
  # to both boxes here which could cause problems depending on what styles
  # are added.
  with me.box(style=merge_styles(_DEFAULT_STYLE, style)):
    with me.box(style=merge_styles(default_flex_style, style)):
      me.slot()


def on_load_embed(e: me.LoadEvent):
  if me.state(ThemeState).dark_mode:
    me.set_theme_mode("dark")
  else:
    me.set_theme_mode("system")


def text_to_text(
    transform: Callable[[str], Generator[str, None, None] | str],
    *,
    title: str | None = None,
    transform_mode: Literal['append', 'replace'] = 'append',
):
  """Creates a simple UI which takes in a text input and returns a text output.

  This function creates event handlers for text input and output operations
  using the provided transform function to process the input and generate the
  output.

  Args:
    transform: Function that takes in a string input and either returns or
      yields a string output.
    title: Headline text to display at the top of the UI
    transform_mode: Specifies how the output should be updated when yielding an
      output using a generator. - "append": Concatenates each new piece of text
      to the existing output. - "replace": Replaces the existing output with
      each new piece of text.

  Returns:
      The user input and the output.
  """

  def on_input(e: me.InputEvent):
    state = me.state(State)
    state.input = e.value

  def on_click_generate(e: me.ClickEvent):
    state = me.state(State)
    output = transform(state.input)
    if isinstance(output, types.GeneratorType):
      for val in output:
        if transform_mode == 'append':
          state.output += val
        elif transform_mode == 'replace':
          state.output = val
        else:
          raise ValueError(f'Unsupported transform_mode: {transform_mode}')
        yield
    else:
      # `output` is a str, however type inference doesn't
      # work w/ generator's unusual ininstance check.
      state.output = cast(str, output)
      yield

  def on_click_clear(e: me.ClickEvent):
    state = me.state(State)
    state.input = ''
    state.textarea_key += 1

  with me.box(
      style=me.Style(
          background=me.theme_var('surface-container-low'),
          height='100%',
      )
  ):
    with me.box(
        style=me.Style(
            background=me.theme_var('surface-container-low'),
            padding=me.Padding(top=24, left=24, right=24, bottom=24),
            display='flex',
            flex_direction='column',
        )
    ):
      if title:
        me.text(title, type='headline-5')
      with me.box(
          style=me.Style(
              margin=me.Margin(left='auto', right='auto'),
              width='min(1024px, 100%)',
              gap='24px',
              flex_grow=1,
              display='flex',
              flex_wrap='wrap',
          )
      ):
        box_style = me.Style(
            flex_basis='max(480px, calc(50% - 48px))',
            background=me.theme_var('surface-container-lowest'),
            border=me.Border.all(
                me.BorderSide(
                    width=1,
                    style='solid'
                    if me.theme_brightness() == 'dark'
                    else 'none',
                    color=me.theme_var('outline'),
                )
            ),
            border_radius=12,
            box_shadow=(
                '0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f'
            ),
            padding=me.Padding(top=16, left=16, right=16, bottom=16),
            display='flex',
            flex_direction='column',
        )
        with me.box(style=box_style):
          me.text('Enter your question here', style=me.Style(font_weight=500))
          me.box(style=me.Style(height=16))
          me.textarea(
              key=str(me.state(State).textarea_key),
              on_input=on_input,
              placeholder='',
              rows=5,
              autosize=True,
              max_rows=15,
              appearance='outline',
              style=me.Style(width='100%'),
          )
          me.box(style=me.Style(height=12))
          with me.box(
              style=me.Style(display='flex', justify_content='space-between')
          ):
            me.button(
                'Clear',
                color='primary',
                type='stroked',
                on_click=on_click_clear,
            )
            me.button(
                'Query',
                color='primary',
                type='flat',
                on_click=on_click_generate,
            )
        with me.box(style=box_style):
          me.text('Answer', style=me.Style(font_weight=500))
          me.markdown(me.state(State).output)
    return me.state(State).input, me.state(State).output

def merge_styles(
    default: me.Style, overrides: me.Style | None = None
) -> me.Style:
  """Merges two styles together.

  Args:
    default: The starting style
    overrides: Any set styles will override styles in default

  Returns:
    A new style object with the merged styles.
  """
  if not overrides:
    overrides = me.Style()

  default_fields = {
      field.name: getattr(default, field.name) for field in fields(me.Style)
  }
  override_fields = {
      field.name: getattr(overrides, field.name)
      for field in fields(me.Style)
      if getattr(overrides, field.name) is not None
  }

  return me.Style(**default_fields | override_fields)


_DEFAULT_STYLE = me.Style(
    background=me.theme_var('surface-container'),
    border=me.Border.symmetric(
        vertical=me.BorderSide(
            width=1,
            style='solid',
            color=me.theme_var('outline-variant'),
        )
    ),
    padding=me.Padding.all(10),
)

_DEFAULT_FLEX_STYLE = me.Style(
    align_items='center',
    display='flex',
    gap=5,
    justify_content='space-between',
)

_DEFAULT_MOBILE_FLEX_STYLE = me.Style(
    align_items='center',
    display='flex',
    flex_direction='column',
    gap=12,
    justify_content='center',
)


@me.content_component
def header_section():
  """Adds a section to the header."""
  with me.box(style=me.Style(display='flex', gap=5)):
    me.slot()


def on_feedback(isup: bool):
  state = me.state(FeedbackState)
  state.feedback = 'Thumbs up' if isup else 'Thumbs down'
  state.ask_reason = True


def on_reason_input(e: me.InputEvent):
  state = me.state(FeedbackState)
  state.reason = e.value

@me.stateclass
class ThemeState:
  dark_mode: bool


def toggle_theme(e: me.ClickEvent):
  if me.theme_brightness() == "light":
    me.set_theme_mode("dark")
    me.state(ThemeState).dark_mode = True
  else:
    me.set_theme_mode("light")
    me.state(ThemeState).dark_mode = False


def add_header():
  with me.box(style=me.Style(margin=me.Margin(bottom=0))):
    with header(max_width=None, style=me.Style(justify_content='center')):
      with header_section():
        me.text(
            'LLM-powered Q&A System',
            type='headline-4',
            style=me.Style(
                margin=me.Margin(bottom=0),
                padding=me.Padding.symmetric(vertical=30, horizontal=15),
            ),
        )
        with me.content_button(
            type='icon',
            style=me.Style(left=8, right=4, top=4),
            on_click=toggle_theme,
        ):
          me.icon(
              'light_mode' if me.theme_brightness() == 'dark' else 'dark_mode'
          )


def add_feedback_section(state: FeedbackState):
  """
  Args:
    state:
  """
  with me.box(style=me.Style(margin=me.Margin(bottom=0))):
    with header(
        max_width=None, style=me.Style(background='#99b8cb', color='#212f3d')
    ):
      with header_section():
        with me.box(
            style=me.Style(display='flex', flex_direction='row', gap=15)
        ):
          me.text(
              'Share your feedback:',
              type='subtitle-2',
              style=me.Style(margin=me.Margin(top=10)),
          )
          with me.content_button(
              type='icon', on_click=lambda _: on_feedback(True)
          ):
            me.icon('thumb_up')
          with me.content_button(
              type='icon', on_click=lambda _: on_feedback(False)
          ):
            me.icon('thumb_down')

        if state.ask_reason:
          with me.box(style=me.Style(margin=me.Margin(top=0))):
            me.textarea(
                placeholder='Tell us why',
                rows=1,
                on_input=on_reason_input,
                subscript_sizing='dynamic',
            )

        if state.feedback:
          with me.box(style=me.Style(margin=me.Margin(top=0))):
            me.text(
                f'\n{state.feedback} submitted',
                type='subtitle-2',
                style=me.Style(margin=me.Margin(top=10)),
            )
            if state.reason:
              me.text(
                  f'Reason: {state.reason}',
                  type='subtitle-2',
                  style=me.Style(margin=me.Margin(top=10)),
              )

def add_subsection():
  with me.box(
      style=me.Style(
          margin=me.Margin(left='auto', right='auto'),
          width='min(1024px, 100%)',
          gap='2px',
          flex_grow=1,
          display='flex',
          flex_wrap='wrap',
      )
  ):
    me.markdown(
        "I'm an LLM-powered agent with access to the dataset you provided "
        "(we use syenthsis Store data here as an example). I can"
        " provide transparent reasoning for my responses. You can ask me"
        " questions like: \n* ***How many stores in the US?*** "
        "\n* ***Which store have the most products??*** "
        "\n* ***The top 3 stores with the most customers last year?***\n",

        style=me.Style(
            align_items='center',
            margin=me.Margin(bottom=10),
            padding=me.Padding.symmetric(vertical=0),
        ),
    )
    me.html(
      """
      Contact me at Haoyuan Zhang in 
      <a href="https://www.linkedin.com/in/haoyuan-z-b4541492/" target="_blank">Linkedin</a>
      """,
      mode="sanitized",
    )

def add_warning_section():
  with me.box(
      style=me.Style(
          background='green',
          height=50,
          margin=me.Margin.symmetric(vertical=24, horizontal=12),
          border=me.Border.symmetric(
              horizontal=me.BorderSide(width=2, color='black', style='groove')
          ),
      )
    ):
      me.markdown(
          ' Note: I only have'
          ' access to the data generated as an example, you can easily change it to your own'
          ' dataset and defined the table schema for your own use',
          style=me.Style(
              align_items='center', margin=me.Margin(bottom=0), color='cyan'
          ),
      )

@me.page(
  security_policy=me.SecurityPolicy(
    allowed_iframe_parents=["https://huggingface.co"]
  ),
  title="LLM QA System",
  on_load=on_load_embed,
)
def app():
  """ """
  feedback_state = me.state(FeedbackState)

  add_header()
  add_feedback_section(feedback_state)
  add_subsection()
  add_warning_section()

  gemini_react_chat = react.ReAct(
      model='models/gemini-2.0-flash',
      ReAct_prompt= prompt.get_prompt(),
  )

  def transform(text: str) -> str:
    response, final_answer = gemini_react_chat(text, temperature=0.0)
    response = (
        '```\n' + final_answer + '\n```' + '\n\n## Gemini 2.0 Flash: \n' + response
    )
    return response

  user_input, user_output = text_to_text(transform)

