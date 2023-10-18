from typing import NewType, Union

Homework = NewType('Homework', dict[str, Union[int, str]])

JSONAnswer = NewType('JSONAnswer', dict[str, Union[int, list[Homework]]])
