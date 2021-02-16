from __future__ import annotations
from .pane import Pane
from ..can import Message, MessageType, MessageTable
import curses


class MessagePane(Pane):
    """A derivative of Pane customized specifically to list miscellaneous CAN
    messages stored in a MessageTable

    :param name: The name of the pane (to be printed in the top left)
    :type name: str

    :param cols: A dictionary describing the pane layout. The key is the Pane
        collumn name, the value is a tuple containing the Message attribute to
        map the collumn to, and the max collumn width respectively.
    :type cols: dict

    :param selected: An indicator that the current Pane is selected
    :type selected: bool

    :param table: The message table
    :type table: MessageTable
    """

    def __init__(self: MessagePane,
                 cols: dict,
                 types: [MessageType],
                 name: str = '',
                 parent: any = None,
                 height: int = 1,
                 width: int = 1,
                 y: int = 0,
                 x: int = 0,
                 message_table: MessageTable = MessageTable()):
        super().__init__(parent=(parent or curses.newpad(0, 0)),
                         height=height,
                         width=width,
                         y=y,
                         x=x)

        # Pane details
        self._name = name
        self.cols = cols
        self.types = types
        self.__top = 0
        self.__top_max = 0
        self.__col_sep = 2
        self.__header_style = curses.color_pair(4)
        self.table = message_table

        # Cursor stuff
        self.cursor = 0
        self.cursor_min = 0
        self.cursor_max = self.d_height - 10

        # Reset the collumn widths to the minimum size of the collumn names
        self.__reset_col_widths()

    def resize(self: MessagePane, height: int, width: int) -> None:
        """A wrapper for `Pane.resize()`. This intercepts a call for a resize
        in order to upate MessagePane-specific details that change on a resize
        event. The parent `resize()` gets called first and then MessagePane's
        details are updated.

        :param height: New virtual height
        :type height: int

        :param width: New virtual width
        :type width: int
        """
        super().resize(height, width)
        p_height = self.d_height - 3
        self.cursor_max = len(self.table) if len(self.table) < p_height else p_height
        occluded = len(self.__filter_messages()) - self.__top - self.cursor_max
        self.__top_max = occluded if occluded > 0 else 0

    def _reset_scroll_positions(self: MessagePane) -> None:
        self.cursor = self.cursor_max
        self.scroll_position_y = 0
        self.scroll_position_x = 0

    @property
    def scroll_limit_y(self: MessagePane) -> int:
        """The maximim rows the pad is allowed to shift by when scrolling
        """
        return self.d_height - 2

    @property
    def scroll_limit_x(self: MessagePane) -> int:
        """The maximim columns the pad is allowed to shift by when scrolling
        """
        max_length = sum(list(map(lambda x: x[1], self.cols.values())))
        occluded = max_length - self.d_width + 7
        return occluded if(occluded > 0) else 0

    def scroll_up(self: MessagePane, rate: int = 1) -> None:
        """This overrides `Pane.scroll_up()`. Instead of shifting the
        pad vertically, the slice of messages from the `MessageTable` is
        shifted.

        :param rate: Number of messages to scroll by
        :type rate: int
        """
        self.cursor -= 1
        if(self.cursor < self.cursor_min):
            self.cursor = self.cursor_min
            self.__top -= 1
            if(self.__top < 0):
                self.__top = 0

    def scroll_down(self: MessagePane, rate: int = 1) -> None:
        """This overrides `Pane.scroll_up()`. Instead of shifting the
        pad vertically, the slice of messages from the `MessageTable` is
        shifted.

        :param rate: Number of messages to scroll by
        :type rate: int
        """
        self.cursor += 1
        if(self.cursor > (self.cursor_max - 1)):
            self.cursor = self.cursor_max - 1
            if(self.__top_max > 0):
                self.__top += 1

    def __filter_messages(self: MessagePane) -> [Message]:
        return self.table.filter(self.types)(self.__top, self.__top + self.d_height - 3)
        # return list(filter(lambda x: (x.type in self.types)
        #                   or (x.supertype in self.types), messages))

    def __draw_header(self: Pane) -> None:
        """Draw the table header at the top of the Pane

        This uses the `cols` dictionary to determine what to write
        """
        self.add_line(0,
                      2,
                      f'{self._name}: ({len(self.table)}'
                      ' messages)'
                      f' ({self.cursor}/{self.d_height - 3})'
                      f' (top: {self.__top}/{self.__top_max})',
                      highlight=self.selected)

        pos = 1
        for name, data in self.cols.items():
            self.add_line(1,
                          pos,
                          f'{name}:'.ljust(data[1] + self.__col_sep, ' '),
                          highlight=True,
                          color=curses.color_pair(4))
            pos += data[1] + self.__col_sep

    def draw(self: MessagePane) -> None:
        """Draw all records from the MessageTable to the Pane
        """
        super().draw()
        p_height, p_width = self.parent.getmaxyx()
        self.resize(p_height, p_width)

        # Get the messages to be displayed based on scroll positioning,
        #   and adjust column widths accordingly
        draw_messages = self.__filter_messages()
        self.__check_col_widths(draw_messages)

        # TODO: Figure out why __check_col_widths consumes draw_messages
        #   Ergo: Why I have to do this again to re-fetch the list
        draw_messages = self.__filter_messages()

        # Draw the header and messages
        self.__draw_header()
        for i, message in enumerate(draw_messages):
            pos = 1
            for name, data in self.cols.items():
                attr = getattr(message, data[0])
                callable = data[2] if (len(data) == 3) else str
                self.add_line(2 + i,
                              pos,
                              callable(attr).ljust(data[1] + self.__col_sep,
                                                   ' '),
                              highlight=(self.cursor == i))
                pos += data[1] + self.__col_sep
            self.add_line(i + 2, 60, f'{self.__top + i}')

        # Refresh the Pane and end the draw cycle
        super().refresh()

    def __reset_col_widths(self: Message):
        for name, data in self.cols.items():
            self.cols[name] = (data[0], len(name), data[2]) \
                if (len(data) == 3) else (data[0], len(name))

    def __check_col_widths(self: MessagePane, messages: [Message]) -> None:
        for message in messages:
            for name, data in self.cols.items():
                attr = getattr(message, data[0])
                attr_len = len(str(attr))
                if(data[1] < attr_len):
                    self.cols[name] = (data[0], attr_len)
                    super().clear()
