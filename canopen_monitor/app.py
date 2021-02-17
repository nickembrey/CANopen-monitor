from __future__ import annotations
import curses
import datetime as dt
from .can import MessageTable, MessageType
from .ui import MessagePane


def pad_hex(value: int) -> str:
    return f'0x{hex(value).upper()[2:].rjust(3, "0")}'


class App:
    """The User Interface
    """

    def __init__(self: App, message_table: MessageTable):
        self.table = message_table
        self.selected_pane_pos = 0
        self.selected_pane = None

    def __enter__(self: App):
        # Monitor setup, take a snapshot of the terminal state
        self.screen = curses.initscr()  # Initialize standard out
        self.screen.scrollok(True)      # Enable window scroll
        self.screen.keypad(True)        # Enable special key input
        self.screen.nodelay(True)       # Disable user-input blocking
        curses.curs_set(False)          # Disable the cursor
        self.__init_color_pairs()       # Enable colors and create pairs

        # Don't initialize any sub-panes or grids until standard io screen has
        #   been initialized
        height, width = self.screen.getmaxyx()
        height -= 1
        self.hb_pane = MessagePane(cols={'Node ID': ('node_name', 0, hex),
                                         'State': ('state', 0),
                                         'Status': ('message', 0)},
                                   types=[MessageType.HEARTBEAT],
                                   parent=self.screen,
                                   height=int(height / 2) - 1,
                                   width=width,
                                   y=1,
                                   x=0,
                                   name='Heartbeats',
                                   message_table=self.table)
        self.misc_pane = MessagePane(cols={'COB ID': ('arb_id', 0, pad_hex),
                                           'Node Name': ('node_name', 0, hex),
                                           'Type': ('type', 0),
                                           'Message': ('message', 0)},
                                     types=[MessageType.NMT,
                                            MessageType.SYNC,
                                            MessageType.TIME,
                                            MessageType.EMER,
                                            MessageType.SDO,
                                            MessageType.PDO],
                                     parent=self.screen,
                                     height=int(height / 2),
                                     width=width,
                                     y=int(height / 2),
                                     x=0,
                                     name='Miscellaneous',
                                     message_table=self.table)
        self.__select_pane(self.hb_pane, 0)
        return self

    def __exit__(self: App, type, value, traceback) -> None:
        # Monitor destruction, restore terminal state
        curses.nocbreak()       # Re-enable line-buffering
        curses.noecho()         # Enable user-input echo
        curses.curs_set(True)   # Enable the cursor
        curses.resetty()        # Restore the terminal state
        curses.endwin()         # Destroy the virtual screen

    def _handle_keyboard_input(self: App) -> None:
        """This is only a temporary implementation

        .. deprecated::

            Soon to be removed
        """
        # Grab user input
        input = self.screen.getch()
        curses.flushinp()

        if(input == curses.KEY_UP):
            self.selected_pane.scroll_up()
        elif(input == curses.KEY_DOWN):
            self.selected_pane.scroll_down()
        elif(input == 337):  # Shift + Up
            self.selected_pane.scroll_up(rate=16)
        elif(input == 336):  # Shift + Down
            self.selected_pane.scroll_down(rate=16)
        elif(input == curses.KEY_LEFT):
            self.selected_pane.scroll_left(rate=4)
        elif(input == curses.KEY_RIGHT):
            self.selected_pane.scroll_right(rate=4)
        elif(input == curses.KEY_RESIZE):
            self.hb_pane._reset_scroll_positions()
            self.misc_pane._reset_scroll_positions()
            self.screen.clear()
        elif(input == 567):  # Ctrl + Up
            self.__select_pane(self.hb_pane, 0)
        elif(input == 526):  # Ctrl + Down
            self.__select_pane(self.misc_pane, 1)

    def __init_color_pairs(self: App) -> None:
        curses.start_color()
        # Implied: color pair 0 is standard black and white
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    def __select_pane(self: App, pane: MessagePane, pos: int) -> None:
        # Only undo previous selection if there was any
        if(self.selected_pane is not None):
            self.selected_pane.selected = False

        # Select the new pane and change internal Pane state to indicate it
        self.selected_pane = pane
        self.selected_pane_pos = pos
        self.selected_pane.selected = True

    def __draw_header(self: App, ifaces: [tuple]) -> None:
        # Draw the timestamp
        date_str = f'{dt.datetime.now().ctime()},'
        self.screen.addstr(0, 0, date_str)
        pos = len(date_str) + 1

        # Draw the interfaces
        for iface in ifaces:
            color = curses.color_pair(1) if iface[1] else curses.color_pair(3)
            sl = len(iface[0])
            self.screen.addstr(0, pos, iface[0], color)
            pos += sl + 1

    def __draw__footer(self: App) -> None:
        height, width = self.screen.getmaxyx()
        footer = '<F1>: Info, <F2>: Hotkeys'
        self.screen.addstr(height - 1, 1, footer)

    def draw(self: App, ifaces: [tuple]):
        self.__draw_header(ifaces)
        self.hb_pane.draw()
        self.misc_pane.draw()
        self.__draw__footer()

    def refresh(self: App):
        self.screen.refresh()
